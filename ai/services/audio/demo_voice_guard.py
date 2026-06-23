"""
services/audio/demo_voice_guard.py
───────────────────────────────────
Demonstration CLI script for the AI Interviewer Voice Guard.
Runs either a real-time mic/PyAnnote diarization test or a simulated mock test.

Usage:
  python demo_voice_guard.py --mock
  python demo_voice_guard.py --real --hf-token <YOUR_HF_TOKEN>
"""

import sys
import os
import argparse
import time
from typing import Any

# Ensure we can import from the relative path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.audio.voice_guard import AIInterviewerVoiceGuard

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    sd = None
    np = None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demo of AIInterviewerVoiceGuard with speaker enrollment and state machine."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--mock",
        action="store_true",
        help="Run in Simulated/Mock Mode (no GPU/HF Token/microphone required)",
    )
    group.add_argument(
        "--real",
        action="store_true",
        help="Run in Real Mode (requires GPU/HF Token/microphone)",
    )
    parser.add_argument(
        "--hf-token",
        type=str,
        default=None,
        help="Hugging Face access token for PyAnnote model access",
    )
    parser.add_argument(
        "--enroll-file",
        type=str,
        default=None,
        help="Optional path to a pre-recorded WAV file to enroll candidate voice",
    )
    args = parser.parse_args()

    # Pre-flight check
    if args.real:
        if sd is None or np is None:
            print("[Error] sounddevice and numpy must be installed to run in Real Mode.")
            sys.exit(1)
        hf_token = args.hf_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            print("[Error] Hugging Face Access Token is required to run PyAnnote models.")
            print("Please pass --hf-token or set the HF_TOKEN environment variable.")
            sys.exit(1)

    print("=" * 60)
    print("       Auralis · AI Interviewer Voice Guard Demonstration")
    print("=" * 60)
    print(f"Mode: {'SIMULATED/MOCK' if args.mock else 'REAL-TIME AUDIO'}")
    print("=" * 60)

    # 1. Initialize Voice Guard
    guard = AIInterviewerVoiceGuard(
        hf_token=args.hf_token,
        mock=args.mock,
        sample_rate=16000,
        window_duration=4.0,
        step_duration=1.0,
        threshold=0.80,
    )

    # 2. Speaker Enrollment
    enrollment_sample = None
    if args.mock:
        print("\n[Step 1] Speaker Enrollment (Mock Mode)")
        print("Simulating a 10-second candidate voice sample...")
        guard.enroll_speaker(None)
    else:
        print("\n[Step 1] Speaker Enrollment (Real Mode)")
        if args.enroll_file:
            print(f"Loading enrollment voice sample from: {args.enroll_file}")
            enrollment_sample = args.enroll_file
        else:
            print("No enrollment file provided. We will record 10 seconds of your voice.")
            print("Prepare to speak, then press ENTER to start recording...")
            input()
            
            sample_rate = 16000
            duration = 10.0  # seconds
            print("🔴 RECORDING... Speak naturally into the microphone...")
            
            # Record float32 mono
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
            )
            
            # Print a simple progress bar
            for i in range(int(duration)):
                sys.stdout.write(f"\r[{'#' * (i + 1)}{'.' * (int(duration) - i - 1)}] {i+1}s / {int(duration)}s")
                sys.stdout.flush()
                time.sleep(1.0)
                
            sd.wait()
            print("\n🟢 Recording finished!")
            enrollment_sample = recording

        guard.enroll_speaker(enrollment_sample)

    # 3. Define Callback for Completed Responses
    def on_response_complete(response_audio: Any) -> None:
        print("\n" + "=" * 50)
        print("🎉 [Callback] Callback Triggered: Candidate response completed!")
        print(f"   Details: {response_audio}")
        print("=" * 50 + "\n")

    # 4. Start Listening Loop
    print("\n[Step 2] Launching AI Interviewer Voice Guard Loop...")
    guard.start_listening(on_response_complete)

    try:
        if args.mock:
            # Let the mock simulation run its course
            while guard.is_listening:
                time.sleep(0.5)
        else:
            print("Listening in real-time... Speak into your microphone.")
            print("If you speak alone, it is normal.")
            print("If a second speaker talks, or you speak with someone else, it will trigger an alert.")
            print("Press Ctrl+C to stop the session at any time.")
            while guard.is_listening:
                time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n⏹ Stopping session...")
        guard.stop_listening()
    finally:
        print("\n" + "=" * 60)
        print("                     Session Summary")
        print("=" * 60)
        print(f"Total warnings given : {guard.intruder_count}")
        print(f"Final State          : {guard.state}")
        print("\nConversation Log:")
        for role, text in guard.transcript:
            print(f"  [{role}]: {text}")
        print("=" * 60)
        print("Done.")


if __name__ == "__main__":
    main()
