"""
core/assistant.py
──────────────────
VoiceAssistant — top-level orchestrator for the Gemini Live Voice
Interview Assistant.

This class wires together all service modules:

    shared.config   → constants (model IDs, audio params, paths)
    shared.ui       → terminal output helpers
    services.memory → LangGraph memory graph + prompt builder
    services.audio  → AudioManager (streams + async send/receive loops)
    services.resume → resume parsing and system-prompt embedding
    services.judge  → LLM-as-Judge post-interview scorecard

It owns:
  • The google-genai client and Live API session lifecycle
  • The per-session transcript (saved to chats/ on shutdown)
  • The _on_turn_complete callback that bridges audio → memory
  • The stop() method called by the signal handler in main.py
"""

import asyncio
import traceback
import os
from datetime import datetime

from google import genai          # type: ignore
from google.genai import types    # type: ignore

from shared.config import (
    API_KEY,
    MODEL,
    VOICE_NAME,
    SPEECH_LANGUAGE_CODE,
    BASE_SYSTEM_INSTRUCTION,
    MEMORY_FILE,
    CHATS_DIR,
    RESUME_FILE,
)
from shared.ui import Colors, print_banner, print_status, print_event, print_error
from services.memory  import load_memory, build_memory_graph, build_system_prompt
from services.audio   import AudioManager
from services.resume  import load_resume_context
from services.judge   import run_judge, print_report


class VoiceAssistant:
    """
    Orchestrates the full voice interview session:

        1. Load persisted memory from disk
        2. Optionally parse and embed the candidate's resume
        3. Build the Gemini system instruction (base + memory + resume)
        4. Open audio streams
        5. Connect to Gemini Live API
        6. Run send + receive tasks concurrently
        7. On shutdown: run LLM-as-Judge, save transcript + scorecard
    """

    def __init__(self, resume_path: str | None = None) -> None:
        self._client     = genai.Client(api_key=API_KEY)
        self._is_running = False

        # Task handles kept for clean cancellation on Ctrl+C
        self._send_task = None
        self._recv_task = None

        # Per-session transcript entries: (timestamp, role, text)
        self._transcript:    list[tuple[str, str, str]] = []
        self._session_start: datetime | None            = None

        # ── Resume context ───────────────────────────
        _resume_path = resume_path or RESUME_FILE
        self._resume_context: str = load_resume_context(_resume_path)

        # ── Memory ───────────────────────────────────
        self._memory_graph = build_memory_graph()
        self._memory_state = load_memory()

        if self._memory_state["summary"] or self._memory_state["raw_turns"]:
            print_status("Previous memory loaded ✓", Colors.CYAN)
        else:
            print_status("No prior memory found — starting fresh", Colors.DIM)

        # ── Audio manager (callback wired in) ────────
        self._audio = AudioManager(on_turn_complete=self._on_turn_complete)

    # ── Transcript ────────────────────────────────────

    def _log(self, role: str, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._transcript.append((timestamp, role, text.strip()))

    def _save_transcript(self, report=None) -> None:
        """Write the session transcript (and optional scorecard) to chats/<timestamp>.txt."""
        if not self._transcript:
            print_status("No conversation to save.", Colors.YELLOW)
            return

        os.makedirs(CHATS_DIR, exist_ok=True)
        filename = f"chat_{self._session_start.strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(CHATS_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("  GEMINI LIVE VOICE INTERVIEW — CHAT TRANSCRIPT\n")
            f.write("=" * 60 + "\n")
            f.write(f"  Date   : {self._session_start.strftime('%Y-%m-%d')}\n")
            f.write(f"  Model  : {MODEL}\n")
            f.write(f"  Voice  : {VOICE_NAME}\n")
            f.write(f"  Start  : {self._session_start.strftime('%H:%M:%S')}\n")
            f.write(f"  End    : {datetime.now().strftime('%H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

            for timestamp, role, text in self._transcript:
                icon = "🎤" if role == "You" else "🤖"
                f.write(f"[{timestamp}]  {icon} {role}:\n  {text}\n\n")

            f.write("=" * 60 + "\n  END OF TRANSCRIPT\n" + "=" * 60 + "\n")

            # Append scorecard if available
            if report:
                f.write("\n" + "=" * 60 + "\n")
                f.write("  INTERVIEW SCORECARD (LLM-as-Judge)\n")
                f.write("=" * 60 + "\n\n")
                for dim in report.dimensions:
                    f.write(f"  {dim.name}: {dim.score}/10\n")
                    f.write(f"    {dim.rationale}\n\n")
                f.write(f"  Overall Score: {report.overall_score:.1f}/10\n")
                f.write(f"  Hire Recommendation: {report.hire_recommendation}\n\n")
                if report.overall_verdict:
                    f.write(f"  Verdict:\n  {report.overall_verdict}\n\n")
                if report.strengths:
                    f.write("  Strengths:\n")
                    for s in report.strengths:
                        f.write(f"    • {s}\n")
                    f.write("\n")
                if report.improvements:
                    f.write("  Areas for Improvement:\n")
                    for imp in report.improvements:
                        f.write(f"    • {imp}\n")
                    f.write("\n")
                f.write("=" * 60 + "\n")

        print_event(f"Chat saved → {filepath}", Colors.CYAN)

    # ── Turn-complete callback (audio → memory bridge) ──

    async def _on_turn_complete(self, user_text: str, assistant_text: str) -> None:
        """
        Called by AudioManager at the end of every completed (or interrupted) turn.
        Logs to transcript and runs the LangGraph memory pipeline in an executor.
        """
        self._log("You",    user_text)
        self._log("Gemini", assistant_text)

        await asyncio.get_event_loop().run_in_executor(
            None, self._update_memory, user_text, assistant_text
        )

    def _update_memory(self, user_text: str, assistant_text: str) -> None:
        """Synchronous wrapper — runs the LangGraph graph for one exchange."""
        new_state = dict(self._memory_state)
        new_state["new_turn"]         = {"user": user_text, "assistant": assistant_text}
        new_state["should_summarise"] = False

        try:
            result             = self._memory_graph.invoke(new_state)
            self._memory_state = result
        except Exception as e:
            print_error(f"Memory update failed: {e}")

    # ── Session control ───────────────────────────────

    def stop(self) -> None:
        """Signal all tasks to stop. Called by the signal handler in main.py."""
        self._is_running       = False
        self._audio.is_running = False

        for task in (self._send_task, self._recv_task):
            if task and not task.done():
                task.cancel()

    # ── Main run loop ─────────────────────────────────

    async def run(self) -> None:
        """
        Full session lifecycle:
            open audio → connect to Gemini → stream → judge → teardown
        """
        self._session_start = datetime.now()
        print_banner(MODEL, VOICE_NAME)
        print_status("Initializing audio devices...")

        try:
            self._audio.open()
        except Exception as e:
            print_error(f"Failed to initialize audio: {e}")
            print_error("Make sure a microphone and speakers are connected.")
            return

        print_status("Audio devices ready ✓")
        print_status(f"Connecting to Gemini ({MODEL})...")

        # Log memory status
        summary   = self._memory_state.get("summary", "")
        raw_turns = self._memory_state.get("raw_turns", [])
        if summary or raw_turns:
            print_status(
                f"Memory active — summary={'yes' if summary else 'no'}, "
                f"buffered turns={len(raw_turns)}",
                Colors.CYAN,
            )

        # Build system instruction: base + memory + resume
        system_instruction = build_system_prompt(
            self._memory_state, BASE_SYSTEM_INSTRUCTION
        )
        if self._resume_context:
            system_instruction = system_instruction + "\n\n" + self._resume_context

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=VOICE_NAME
                    )
                ),
                language_code=SPEECH_LANGUAGE_CODE,
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=system_instruction)]
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )

        try:
            async with self._client.aio.live.connect(
                model=MODEL, config=config
            ) as session:
                print_status("Connected to Gemini ✓")
                print()
                print(
                    f"  {Colors.BOLD}{Colors.GREEN}"
                    f"🟢 Session active — start talking!{Colors.RESET}"
                )
                print(
                    f"  {Colors.DIM}"
                    f"   Press Ctrl+C to end the conversation.{Colors.RESET}"
                )
                print()

                self._is_running       = True
                self._audio.is_running = True

                self._send_task = asyncio.create_task(
                    self._audio.send_loop(session)
                )
                self._recv_task = asyncio.create_task(
                    self._audio.receive_loop(session)
                )

                try:
                    await asyncio.gather(self._send_task, self._recv_task)
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            print_error(f"Connection error: {e}")
            traceback.print_exc()

        finally:
            self._is_running = False
            self._audio.close()
            print()

            # ── LLM-as-Judge evaluation ───────────────────
            report = None
            if self._transcript:
                print_status("Evaluating interview with Gemini judge …", Colors.CYAN)
                try:
                    loop   = asyncio.get_event_loop()
                    report = await loop.run_in_executor(
                        None,
                        run_judge,
                        self._transcript,
                        self._resume_context,
                        API_KEY,
                    )
                except Exception as e:
                    print_error(f"Judge evaluation failed: {e}")

            self._save_transcript(report=report)

            if report:
                print_report(report)

            print_status(f"Memory saved → {MEMORY_FILE}", Colors.CYAN)
            print(f"  {Colors.YELLOW}👋 Session ended. Goodbye!{Colors.RESET}")
            print()
