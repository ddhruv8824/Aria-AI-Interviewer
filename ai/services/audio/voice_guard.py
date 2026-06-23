"""
services/audio/voice_guard.py
──────────────────────────────
VoiceGuard — Real-time speaker diarization and voice verification system.
Handles speaker enrollment, microphone capture, voice fingerprinting,
intruder detection, and state machine management with local TTS.
"""

import os
import time
import asyncio
import threading
import collections
from typing import Callable, Any

# Optional imports handled gracefully
try:
    import numpy as np
except ImportError:
    np = None

try:
    import torch
except ImportError:
    torch = None

try:
    import sounddevice as sd
except ImportError:
    sd = None


class AIInterviewerVoiceGuard:
    """
    Real-time voice guard for the AI Interviewer.
    Monitors input stream for intruders, manages interview states,
    and alerts the candidate when environmental rules are violated.
    """

    def __init__(
        self,
        hf_token: str | None = None,
        mock: bool = False,
        sample_rate: int = 16000,
        window_duration: float = 4.0,
        step_duration: float = 1.0,
        threshold: float = 0.80,
        cooldown_duration: float = 9.0,
    ) -> None:
        """
        Initialize the voice guard.
        
        Args:
            hf_token: Hugging Face token required for PyAnnote models.
            mock: If True, operates in Simulated/Mock Mode without physical dependencies.
            sample_rate: Microphone sampling rate (expects 16000Hz).
            window_duration: Size of the sliding window in seconds (e.g., 4.0s).
            step_duration: How often the sliding window runs inference in seconds (e.g., 1.0s).
            threshold: Cosine similarity threshold for speaker verification.
            cooldown_duration: Safety cooldown (seconds) between repeated spoken warnings.
        """
        self.hf_token = hf_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        self.mock = mock
        self.sample_rate = sample_rate
        self.window_duration = window_duration
        self.step_duration = step_duration
        self.threshold = threshold
        self.cooldown_duration = cooldown_duration

        # State machine
        # States: LISTENING, INTRUDER_DETECTED, WAITING_FOR_CONFIRMATION, RESUMING, ENDED
        self.state = "LISTENING"
        self.intruder_count = 0
        self.last_warning_time = 0.0

        # Background processing
        self.is_listening = False
        self.listen_thread = None
        self._audio_chunks = collections.deque(
            maxlen=int(window_duration / step_duration)
        )

        # PyAnnote models (lazy-loaded)
        self.pipeline = None
        self.embedding_model = None
        self.embedding_inference = None
        self.enrolled_embedding = None
        self.device = None

        # Session transcript log
        self.transcript: list[tuple[str, str]] = []

        if self.mock:
            print("[VoiceGuard] Initialized in SIMULATED/MOCK Mode.")
        else:
            print("[VoiceGuard] Initialized in REAL Mode.")
            if not self.hf_token:
                print(
                    "[Warning] No HuggingFace Token provided. "
                    "Make sure to set HF_TOKEN environment variable or supply it during initialization. "
                    "Otherwise, running in Real Mode will fail."
                )

    def load_models(self) -> None:
        """Lazy load PyAnnote pipelines and embedding models using HF Token."""
        if self.mock or self.pipeline is not None:
            return

        print("\n[VoiceGuard] Loading PyAnnote models from Hugging Face...")
        if not self.hf_token:
            raise ValueError(
                "Hugging Face Token (HF_TOKEN) is required to download PyAnnote models. "
                "Please pass it to the constructor or set the environment variable."
            )

        from pyannote.audio import Pipeline, Model, Inference

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[VoiceGuard] Using computation device: {self.device}")

        # Load speaker diarization pipeline
        self.pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=self.hf_token
        )
        self.pipeline.to(self.device)

        # Load speaker embedding extraction model
        self.embedding_model = Model.from_pretrained(
            "pyannote/embedding",
            use_auth_token=self.hf_token
        )
        self.embedding_inference = Inference(
            self.embedding_model,
            window="whole"
        )
        print("[VoiceGuard] PyAnnote models loaded successfully.\n")

    def enroll_speaker(self, audio_sample: Any) -> None:
        """
        Record or load a voice sample from the interviewee to establish
        a voice fingerprint (speaker embedding).
        
        Args:
            audio_sample: Filepath (str) or Numpy Array (PCM float32).
        """
        self.load_models()
        print("[VoiceGuard] Enrolling speaker voice fingerprint...")

        if self.mock:
            # Fake speaker fingerprint in mock mode
            self.enrolled_embedding = np.ones(512, dtype=np.float32)
            time.sleep(1.0)
            print("[VoiceGuard] Mock Speaker enrollment complete.")
            return

        if isinstance(audio_sample, str):
            # Load file path directly
            self.enrolled_embedding = self.embedding_inference(audio_sample)
        elif isinstance(audio_sample, np.ndarray):
            # Process in-memory numpy array
            waveform = torch.tensor(audio_sample, dtype=torch.float32)
            if waveform.ndim == 1:
                waveform = waveform.unsqueeze(0)  # Shape: (1, samples)
            elif waveform.ndim == 2:
                # sounddevice records as (samples, channels), transpose to (channels, samples)
                if waveform.shape[0] > waveform.shape[1]:
                    waveform = waveform.t()
            
            # Ensure mono (downmix if stereo)
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)

            self.enrolled_embedding = self.embedding_inference(
                {"waveform": waveform, "sample_rate": self.sample_rate}
            )
        else:
            raise ValueError(
                "Unsupported audio_sample type. Must be a WAV file path (str) or numpy array."
            )

        print("[VoiceGuard] Speaker enrollment complete. Voice fingerprint generated.")

    def check_for_intruder(self, chunk: Any) -> bool:
        """
        Analyze an audio chunk (sliding window) to detect voice intrusion.
        
        Returns:
            True if:
              - Multiple unique speakers are detected.
              - The speaker's voice fingerprint fails similarity matching (< threshold).
            False if:
              - Only the enrolled candidate is speaking (or silence is present).
        """
        if self.mock:
            # Mock behavior is driven by the simulation timeline in start_listening
            return False

        self.load_models()

        # Convert numpy array to torch tensor
        waveform = torch.tensor(chunk, dtype=torch.float32)
        if waveform.ndim == 1:
            waveform = waveform.unsqueeze(0)
        elif waveform.ndim == 2:
            if waveform.shape[0] > waveform.shape[1]:
                waveform = waveform.t()

        # Ensure mono
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        audio_dict = {"waveform": waveform, "sample_rate": self.sample_rate}

        # 1. Run Diarization Pipeline
        try:
            diarization = self.pipeline(audio_dict)
        except Exception as e:
            print(f"[VoiceGuard Error] Diarization failed: {e}")
            return False

        unique_speakers = list(diarization.labels())

        # If silence or no speech segments
        if len(unique_speakers) == 0:
            return False

        # If more than 1 speaker detected in the chunk, trigger intrusion instantly
        if len(unique_speakers) > 1:
            print(f"[VoiceGuard] Diarization: MULTIPLE speakers detected: {unique_speakers}")
            return True

        # Exactly 1 speaker detected: verify identity using embeddings
        speaker_label = unique_speakers[0]
        turns = [
            segment
            for segment, _, label in diarization.itertracks(yield_label=True)
            if label == speaker_label
        ]

        if not turns:
            return False

        # Extract and concatenate all speech turns for this speaker
        segments_audio = []
        for turn in turns:
            start_sample = int(turn.start * self.sample_rate)
            end_sample = int(turn.end * self.sample_rate)
            
            # Boundary checks
            start_sample = max(0, min(start_sample, waveform.shape[1]))
            end_sample = max(0, min(end_sample, waveform.shape[1]))

            if end_sample > start_sample:
                segments_audio.append(waveform[:, start_sample:end_sample])

        if not segments_audio:
            return False

        speaker_waveform = torch.cat(segments_audio, dim=1)

        try:
            # Extract current speaker embedding
            speaker_embedding = self.embedding_inference(
                {"waveform": speaker_waveform, "sample_rate": self.sample_rate}
            )

            # Cosine similarity calculation
            emb_enrolled = torch.tensor(self.enrolled_embedding)
            emb_current = torch.tensor(speaker_embedding)

            if emb_enrolled.ndim == 1:
                emb_enrolled = emb_enrolled.unsqueeze(0)
            if emb_current.ndim == 1:
                emb_current = emb_current.unsqueeze(0)

            emb_enrolled_norm = torch.nn.functional.normalize(emb_enrolled, p=2, dim=1)
            emb_current_norm = torch.nn.functional.normalize(emb_current, p=2, dim=1)

            similarity = torch.nn.functional.cosine_similarity(
                emb_enrolled_norm, emb_current_norm
            ).item()

            print(f"[VoiceGuard] Speaker matched. Similarity score: {similarity:.4f}")

            # If the speaker does not match the enrolled profile, trigger warning
            if similarity < self.threshold:
                print(f"[VoiceGuard] Speaker verification FAILED ({similarity:.4f} < {self.threshold})")
                return True

        except Exception as e:
            print(f"[VoiceGuard Error] Embedding extraction/matching failed: {e}")

        return False

    def show_popup_alert(self, message: str) -> None:
        """
        Displays a native graphical pop-up warning dialog to alert the candidate.
        Blocks execution until the user clicks OK.
        """
        print(f"\n⚠️  [Pop-up Alert] Displaying Alert: \"{message}\"\n")
        self.transcript.append(("Alert", message))
        
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            # Initialize a hidden tkinter root window
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)  # Make it stay on top
            
            messagebox.showwarning(
                title="Voice Intrusion Detected",
                message=message
            )
            root.destroy()
        except Exception as e:
            # Fallback if tkinter is not available (e.g. headless environment)
            print(f"[VoiceGuard Warning] Failed to display Tkinter pop-up: {e}")
            # Just print and sleep to simulate
            time.sleep(3.0)

    def handle_intruder(self) -> None:
        """Trigger a pop-up warning alert and pause the interview progression."""
        self.state = "INTRUDER_DETECTED"
        print(f"[State Machine] State changed to: {self.state}")

        # Natural, conversational warnings
        warnings = [
            "I can hear another voice in the room. Could you please make sure you're alone before we continue?",
            "It sounds like someone else is speaking. Please find a quiet space and let me know when you're ready.",
        ]
        # Alternate warnings based on count
        warning_msg = warnings[(self.intruder_count - 1) % len(warnings)]

        print(f"[VoiceGuard Alert] Intruder alert {self.intruder_count}/3 triggered.")
        
        # Display the graphical warning pop-up
        self.show_popup_alert(warning_msg)

        self.state = "WAITING_FOR_CONFIRMATION"
        print(f"[State Machine] State changed to: {self.state}")
        self.last_warning_time = time.time()

    def resume_interview(self) -> None:
        """Speak natural resuming bridge and return to active listening."""
        self.state = "RESUMING"
        print(f"[State Machine] State changed to: {self.state}")

        bridge = "Great, let's continue where we left off."
        self.speak(bridge)

        self.state = "LISTENING"
        print(f"[State Machine] State changed to: {self.state}")

    def speak(self, text: str) -> None:
        """
        Play text out loud immediately using TTS, blocking execution.
        
        Args:
            text: Text to speak.
        """
        print(f"\n📢 [TTS Output] AI Interviewer (Aria): \"{text}\"\n")
        self.transcript.append(("AI", text))

        # 1. Try ElevenLabs TTS if API key is provided
        eleven_api_key = os.getenv("ELEVENLABS_API_KEY")
        if eleven_api_key:
            try:
                from elevenlabs.client import ElevenLabs
                from elevenlabs import play
                
                # Retrieve voice name/ID (default to 'Aria')
                voice_name = os.getenv("ELEVENLABS_VOICE", "Aria")
                client = ElevenLabs(api_key=eleven_api_key)
                
                audio = client.generate(
                    text=text,
                    voice=voice_name,
                    model="eleven_monolingual_v1"
                )
                
                # Play audio bytes
                play(audio)
                return
            except Exception as e:
                print(f"[VoiceGuard] ElevenLabs TTS failed: {e}. Falling back to pyttsx3.")

        # 2. Try pyttsx3 local offline speech engine with female voice selection
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            
            # Select a female voice to fit "Aria"
            voices = engine.getProperty("voices")
            female_voice = None
            for voice in voices:
                voice_name_lower = voice.name.lower()
                # Common female voice names: Zira, Samantha, Hazel, Victoria, Haruka, etc.
                if any(name in voice_name_lower for name in ["zira", "samantha", "hazel", "victoria", "female"]):
                    female_voice = voice
                    break
            
            if female_voice:
                engine.setProperty("voice", female_voice.id)
                print(f"[VoiceGuard] Selected female voice: {female_voice.name}")
            else:
                # If no explicit female voice found, use the second voice if available
                if len(voices) > 1:
                    engine.setProperty("voice", voices[1].id)
                    
            engine.say(text)
            engine.runAndWait()
            return
        except Exception as e:
            # Fall back to printing and simulating speech delay
            pass

        # 3. Fallback duration simulation (roughly 150 words per minute -> 2.5 words per second)
        words = len(text.split())
        delay = max(2.5, words / 2.5)
        time.sleep(delay)

    def start_listening(self, on_response_complete_callback: Callable[[Any], None]) -> None:
        """
        Start non-blocking real-time listening stream or simulation in a background thread.
        
        Args:
            on_response_complete_callback: Callback when response is safely complete.
        """
        if self.is_listening:
            return

        self.is_listening = True
        self._audio_chunks.clear()

        if self.mock:
            self.listen_thread = threading.Thread(
                target=self._mock_listening_loop,
                args=(on_response_complete_callback,),
                daemon=True,
            )
        else:
            self.listen_thread = threading.Thread(
                target=self._real_listening_loop,
                args=(on_response_complete_callback,),
                daemon=True,
            )

        self.listen_thread.start()

    def stop_listening(self) -> None:
        """Stop the background listening thread."""
        self.is_listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=3.0)
            self.listen_thread = None
        print("[VoiceGuard] Stopped listening stream.")

    def _real_listening_loop(self, on_response_complete_callback: Callable[[Any], None]) -> None:
        """Active recording loop that monitors sounddevice audio."""
        if sd is None or np is None:
            print("[VoiceGuard Error] sounddevice/numpy not found. Cannot run Real Mode.")
            self.is_listening = False
            return

        chunk_samples = int(self.step_duration * self.sample_rate)
        print("[VoiceGuard] Active listening stream starting on hardware microphone...")

        # Initialize sliding window deque with silent segments to avoid partial windows
        for _ in range(self._audio_chunks.maxlen):
            self._audio_chunks.append(np.zeros((chunk_samples, 1), dtype=np.float32))

        try:
            # Create sounddevice input stream
            # Capture mono, float32, sample_rate
            stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=chunk_samples,
            )
            with stream:
                while self.is_listening:
                    # Read block size chunk
                    data, overflowed = stream.read(chunk_samples)
                    if overflowed:
                        print("[VoiceGuard Warning] Microphone input buffer overflowed.")

                    self._audio_chunks.append(data)

                    # Only run check once the sliding window is full
                    if len(self._audio_chunks) == self._audio_chunks.maxlen:
                        # Combine sliding window chunks
                        full_window = np.concatenate(list(self._audio_chunks), axis=0)

                        # Check intrusion status
                        intruder = self.check_for_intruder(full_window)

                        # Process state machine logic
                        if self.state == "LISTENING":
                            if intruder:
                                current_time = time.time()
                                if current_time - self.last_warning_time >= self.cooldown_duration:
                                    self.intruder_count += 1
                                    if self.intruder_count >= 3:
                                        self.state = "ENDED"
                                        self.show_popup_alert(
                                            "It seems like the environment isn't ideal right now. We can reschedule for a better time."
                                        )
                                        self.is_listening = False
                                        break
                                    else:
                                        self.handle_intruder()
                                        self._audio_chunks.clear()
                                        # Repopulate with silence to prevent immediately re-triggering
                                        for _ in range(self._audio_chunks.maxlen):
                                            self._audio_chunks.append(
                                                np.zeros((chunk_samples, 1), dtype=np.float32)
                                            )
                            else:
                                pass

                        elif self.state == "WAITING_FOR_CONFIRMATION":
                            if not intruder:
                                # Candidate is speaking alone or environment is quiet again
                                print("[VoiceGuard] Environment confirmed clean.")
                                self.resume_interview()
                                self._audio_chunks.clear()
                                for _ in range(self._audio_chunks.maxlen):
                                    self._audio_chunks.append(
                                        np.zeros((chunk_samples, 1), dtype=np.float32)
                                    )

                    # Sleep briefly to yield CPU
                    time.sleep(0.01)

        except Exception as e:
            print(f"[VoiceGuard Error] Stream crashed: {e}")
            self.is_listening = False

    def _mock_listening_loop(self, on_response_complete_callback: Callable[[Any], None]) -> None:
        """Simulate real-time interview loop and state transitions chronologically."""
        print("[VoiceGuard Simulation] Starting mock interview timeline loop...")
        
        elapsed = 0
        while self.is_listening:
            time.sleep(1.0)
            elapsed += 1
            print(f"\n[Simulation Time: {elapsed:02d}s] Current state: {self.state}")

            if elapsed <= 5:
                # Normal candidate speaking
                print("[Simulation] Candidate is speaking. No intruder detected.")
                
            elif 6 <= elapsed <= 8:
                # Intruder detected first time
                if self.state == "LISTENING":
                    self.intruder_count += 1
                    self.handle_intruder()
                else:
                    print("[Simulation] Intruder detected. Waiting for confirmation...")
                    
            elif 9 <= elapsed <= 13:
                # Intruder still talking
                print("[Simulation] Diarization detects multiple speakers or foreign speaker. Waiting...")
                
            elif 14 <= elapsed <= 17:
                # Environment returns to single candidate speaker
                if self.state == "WAITING_FOR_CONFIRMATION":
                    print("[Simulation] Environment cleared (single speaker matching fingerprint).")
                    self.resume_interview()
                else:
                    print("[Simulation] Candidate speaking. Environment clean.")
                    
            elif elapsed >= 18:
                # Complete the interview response turns
                if self.state == "LISTENING":
                    print("[Simulation] Candidate finished speaking. Triggering completion callback.")
                    self.transcript.append(("User", "[Completed response audio]"))
                    on_response_complete_callback("[Completed response audio]")
                    self.is_listening = False
                    break

        print("[VoiceGuard Simulation] Mock listening loop finished.")


class SessionVoiceGuardManager:
    """
    Integrates the AIInterviewerVoiceGuard with the FastAPI WebSocket session.
    Buffers incoming client audio samples, performs sliding window calculations,
    and pushes alert/resumption frames to the Next.js frontend client.
    """

    def __init__(
        self,
        websocket: Any,
        voice_guard: AIInterviewerVoiceGuard,
        stop_event: asyncio.Event,
        sample_rate: int = 16000,
        window_duration: float = 4.0,
        step_duration: float = 1.0,
    ) -> None:
        self.ws = websocket
        self.vg = voice_guard
        self.stop_event = stop_event
        self.sample_rate = sample_rate
        self.window_size = int(window_duration * sample_rate)
        self.step_size = int(step_duration * sample_rate)

        self.audio_buffer: list[float] = []
        self.samples_since_last_check = 0

        # Speaker Enrollment state
        self.enrolled = self.vg.mock  # In mock mode, we bypass dynamic enrollment
        self.enrollment_duration = 15.0  # seconds needed to enroll speaker
        self.enrollment_buffer: list[float] = []

    async def add_pcm_chunk(self, pcm_bytes: bytes) -> None:
        """Process an incoming raw 16-bit linear PCM chunk from the browser client."""
        if np is None:
            return

        # Convert 16-bit integer PCM to float32 normalized to [-1.0, 1.0]
        int16_samples = np.frombuffer(pcm_bytes, dtype=np.int16)
        float32_samples = int16_samples.astype(np.float32) / 32768.0

        if not self.enrolled:
            # 1. Accumulate audio for voice enrollment at session start
            self.enrollment_buffer.extend(float32_samples.tolist())
            if len(self.enrollment_buffer) >= int(self.enrollment_duration * self.sample_rate):
                audio_data = np.array(self.enrollment_buffer, dtype=np.float32)
                
                # Enroll speaker in the background executor to keep socket low latency
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.vg.enroll_speaker, audio_data)
                
                self.enrolled = True
                self.enrollment_buffer.clear()
                print("[VoiceGuard] Dynamic Voice Enrollment complete. Starting active monitoring.")
            return

        # 2. Add to active sliding window buffer
        self.audio_buffer.extend(float32_samples.tolist())
        self.samples_since_last_check += len(float32_samples)

        # Truncate buffer to prevent overflow memory leak
        if len(self.audio_buffer) > self.window_size * 2:
            self.audio_buffer = self.audio_buffer[-self.window_size:]

        # Run checks in sliding steps
        if len(self.audio_buffer) >= self.window_size and self.samples_since_last_check >= self.step_size:
            self.samples_since_last_check = 0
            
            chunk = np.array(self.audio_buffer[-self.window_size:], dtype=np.float32)
            
            # Execute check_for_intruder in background thread pool
            loop = asyncio.get_running_loop()
            is_intruder = await loop.run_in_executor(None, self.vg.check_for_intruder, chunk)
            
            await self.handle_check_result(is_intruder)

    async def handle_check_result(self, intruder: bool) -> None:
        """Handle state machine events and push WebSocket alert messages to Next.js."""
        if self.vg.state == "LISTENING":
            if intruder:
                current_time = time.time()
                if current_time - self.vg.last_warning_time >= self.vg.cooldown_duration:
                    self.vg.intruder_count += 1
                    
                    if self.vg.intruder_count >= 3:
                        self.vg.state = "ENDED"
                        # Send critical alert and terminate session
                        try:
                            await self.ws.send_json({
                                "type": "intruder_alert",
                                "message": "It seems like the environment isn't ideal right now. We will end the interview. Please reschedule for a better time."
                            })
                            await self.ws.send_json({"type": "session_ended"})
                        except Exception:
                            pass
                        # Signal the WebSocket loops to stop
                        self.stop_event.set()
                    else:
                        self.vg.state = "INTRUDER_DETECTED"
                        warnings = [
                            "I can hear another voice in the room. Could you please make sure you're alone before we continue?",
                            "It sounds like someone else is speaking. Please find a quiet space and let me know when you're ready.",
                        ]
                        warning_msg = warnings[(self.vg.intruder_count - 1) % len(warnings)]

                        print(f"[VoiceGuard Alert] Session Intruder {self.vg.intruder_count}/3: Pushing alert frame.")
                        try:
                            await self.ws.send_json({
                                "type": "intruder_alert",
                                "message": warning_msg
                            })
                        except Exception:
                            pass
                        
                        self.vg.state = "WAITING_FOR_CONFIRMATION"
                        self.vg.last_warning_time = time.time()

        elif self.vg.state == "WAITING_FOR_CONFIRMATION":
            if not intruder:
                self.vg.state = "RESUMING"
                print("[VoiceGuard] Environment clear. Sending resumption bridge.")
                
                try:
                    # Hide red alert banner on Next.js frontend
                    await self.ws.send_json({"type": "intruder_resolved"})
                except Exception:
                    pass

                # Play resuming bridge verbally (Aria speaks naturally)
                bridge = "Great, let's continue where we left off."
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.vg.speak, bridge)

                self.vg.state = "LISTENING"
