"""
services/audio/manager.py
──────────────────────────
AudioManager — owns every PyAudio resource and the two async streaming
coroutines for the Gemini Live Voice Interview Assistant.

Responsibilities
────────────────
  • Open / close the microphone input stream and speaker output stream
  • send_loop   : reads PCM chunks from the mic and forwards them to
                  the Gemini Live session
  • receive_loop: iterates over server responses, plays audio chunks,
                  prints transcriptions, and fires a callback when a
                  complete turn arrives so the memory layer can be updated

The class is deliberately stateless with respect to memory — it receives
an on_turn_complete callback and calls it with (user_text, assistant_text)
at the end of every turn.  The core assistant orchestrates everything above.
"""

import asyncio
from typing import Callable, Awaitable

import pyaudio

from shared.config import (
    INPUT_SAMPLE_RATE,
    OUTPUT_SAMPLE_RATE,
    CHANNELS,
    CHUNK_SIZE,
)
from shared.ui import Colors, print_event, print_error

# Resolve FORMAT once so pyaudio is only referenced here
_FORMAT = pyaudio.paInt16

# Type alias for the turn-complete callback
TurnCallback = Callable[[str, str], Awaitable[None]]


class AudioManager:
    """
    Manages PyAudio streams and the two async tasks that power the
    bidirectional audio pipeline with the Gemini Live API.

    Usage
    ─────
        mgr = AudioManager(on_turn_complete=my_async_callback)
        mgr.open()
        send_task = asyncio.create_task(mgr.send_loop(session))
        recv_task = asyncio.create_task(mgr.receive_loop(session))
        # … await gather / cancel …
        mgr.close()

    The on_turn_complete callback receives:
        user_text      (str) – transcribed user speech for the turn
        assistant_text (str) – transcribed / text Gemini response
    """

    def __init__(self, on_turn_complete: TurnCallback) -> None:
        self._pa               = pyaudio.PyAudio()
        self._input_stream     = None
        self._output_stream    = None
        self._on_turn_complete = on_turn_complete

        # Buffers accumulate transcription fragments until turn_complete fires
        self._gemini_buf: list[str] = []
        self._user_buf:   list[str] = []

        self._is_playing = False
        self._turn_count = 0
        self.is_running  = False   # set True by the assistant before tasks start

    # ── Stream lifecycle ─────────────────────────

    def open(self) -> None:
        """Open microphone input and speaker output streams."""
        self._input_stream = self._pa.open(
            format=_FORMAT,
            channels=CHANNELS,
            rate=INPUT_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
        self._output_stream = self._pa.open(
            format=_FORMAT,
            channels=CHANNELS,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE,
        )

    def close(self) -> None:
        """Safely stop and close both streams, then terminate PyAudio."""
        for stream in (self._input_stream, self._output_stream):
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
        self._pa.terminate()

    # ── Async send loop ──────────────────────────

    async def send_loop(self, session) -> None:
        """
        Continuously read PCM chunks from the microphone and forward them
        to the Gemini Live session as raw audio blobs.

        Runs until self.is_running is False or an unrecoverable error occurs.
        """
        from google.genai import types  # type: ignore

        print_event("Microphone active — speak now!", Colors.GREEN)

        while self.is_running:
            try:
                data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._input_stream.read(
                        CHUNK_SIZE, exception_on_overflow=False
                    ),
                )
                await session.send_realtime_input(
                    audio=types.Blob(
                        data=data,
                        mime_type=f"audio/pcm;rate={INPUT_SAMPLE_RATE}",
                    )
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.is_running:
                    print_error(f"Audio send error: {e}")
                break

    # ── Async receive loop ───────────────────────

    async def receive_loop(self, session) -> None:
        """
        Iterate over server responses from the Gemini Live session:
          • Play inline audio data through the speaker immediately
          • Collect output transcription fragments into self._gemini_buf
          • Collect input  transcription fragments into self._user_buf
          • On turn_complete: flush buffers, fire on_turn_complete callback
          • On interrupted:   flush buffers with [interrupted] suffix

        Runs until self.is_running is False or an unrecoverable error occurs.
        """
        while self.is_running:
            try:
                async for response in session.receive():
                    if not self.is_running:
                        break

                    self._handle_transcriptions(response)
                    self._handle_audio_parts(response)
                    await self._handle_turn_events(response)

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.is_running:
                    print_error(f"Receive error: {e}")
                break

    # ── Internal response handlers ───────────────

    def _handle_transcriptions(self, response) -> None:
        """Extract input and output transcription text from a response object."""
        try:
            sc = getattr(response, "server_content", None)
            if not sc:
                return

            # Output transcription — Gemini's own speech transcribed to text
            ot = getattr(sc, "output_transcription", None)
            if ot:
                txt = getattr(ot, "text", None) or ""
                if txt.strip():
                    self._gemini_buf.append(txt.strip())
                    print(f"  {Colors.CYAN}   📝 Gemini: {txt.strip()}{Colors.RESET}")

            # Input transcription — user's mic speech transcribed to text
            it = getattr(sc, "input_transcription", None)
            if it:
                txt = getattr(it, "text", None) or ""
                if txt.strip():
                    self._user_buf.append(txt.strip())
                    print(f"  {Colors.GREEN}   🎤 You: {txt.strip()}{Colors.RESET}")

        except Exception:
            pass   # transcription is best-effort; never crash the audio loop

    def _handle_audio_parts(self, response) -> None:
        """Play any inline audio data and capture any inline text parts."""
        server_content = getattr(response, "server_content", None)
        if not server_content:
            return

        model_turn = getattr(server_content, "model_turn", None)
        if not (model_turn and model_turn.parts):
            return

        for part in model_turn.parts:
            # Raw PCM audio → write directly to the output stream
            if part.inline_data and part.inline_data.data:
                if not self._is_playing:
                    self._is_playing = True
                    print_event("Gemini is speaking...", Colors.MAGENTA)
                self._output_stream.write(part.inline_data.data)

            # Text part (rare in audio-mode but possible)
            if part.text:
                self._gemini_buf.append(part.text)
                print(f"\n  {Colors.CYAN}💬 Gemini: {part.text}{Colors.RESET}")

    async def _handle_turn_events(self, response) -> None:
        """
        React to turn_complete and interrupted signals.
        Both flush the text buffers and fire the on_turn_complete callback
        so the memory layer can store the exchange.
        """
        server_content = getattr(response, "server_content", None)
        if not server_content:
            return

        # ── Normal end of turn ──
        if getattr(server_content, "turn_complete", False):
            self._is_playing  = False
            self._turn_count += 1

            assistant_text = (
                " ".join(self._gemini_buf)
                if self._gemini_buf
                else f"[Audio response #{self._turn_count}]"
            )
            user_text = (
                " ".join(self._user_buf)
                if self._user_buf
                else "[inaudible]"
            )

            self._gemini_buf = []
            self._user_buf   = []

            await self._on_turn_complete(user_text, assistant_text)
            print_event("Listening...", Colors.GREEN)

        # ── Barge-in / interruption ──
        if getattr(server_content, "interrupted", False):
            self._is_playing = False

            partial = (
                " ".join(self._gemini_buf) + " [interrupted]"
                if self._gemini_buf
                else "[interrupted]"
            )

            self._gemini_buf = []
            self._user_buf   = []

            await self._on_turn_complete("[interrupted]", partial)
            print_event("(interrupted)", Colors.YELLOW)
