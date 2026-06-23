"""
api/routers/session.py
───────────────────────
WebSocket endpoint bridging browser audio with the Gemini Live API.
"""

from __future__ import annotations

import asyncio
import base64
import json
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google import genai  # type: ignore
from google.genai import types  # type: ignore
from pydantic import ValidationError

from api.exceptions import AppError, BadRequestError, SessionError, SessionTimeoutError
from api.models.ws_messages import (
    ClientAudioMessage,
    ClientBeginCodingMessage,
    ClientCodingSubmitMessage,
    ClientStartMessage,
    ClientStopMessage,
    ServerErrorMessage,
    SessionMetrics,
)
from services.judge import run_judge, JudgeReport
from services.interviews import save_interview_record
from services.memory import build_system_prompt, load_memory
from services.platform import get_company_context_block
from services.audio import AIInterviewerVoiceGuard, SessionVoiceGuardManager
from shared.config import (
    API_KEY,
    BASE_SYSTEM_INSTRUCTION,
    GROQ_API_KEY,
    INPUT_SAMPLE_RATE,
    INTERVIEWER_NAME,
    MODEL,
    SPEECH_LANGUAGE_CODE,
    VOICE_NAME,
)
from shared.coding_problems import CODING_ROUND_TIME_SEC, pick_coding_problem_id
from shared.logging_config import get_logger

router = APIRouter(tags=["Session"])

log = get_logger("session")


async def _send_error(ws: WebSocket, exc: AppError) -> None:
    """Send a structured error frame to the browser."""
    payload = ServerErrorMessage(
        message=exc.message,
        code=exc.code,
    )
    await ws.send_json(payload.model_dump())


@router.websocket("/ws/session")
async def websocket_session(websocket: WebSocket) -> None:
    """Run a full voice interview over a persistent WebSocket connection."""
    session_id = uuid.uuid4().hex[:12]
    session_log = log.bind(session_id=session_id)

    await websocket.accept()
    session_log.info("websocket accepted")

    try:
        await _run_session(websocket, session_id, session_log)
    except WebSocketDisconnect:
        session_log.info("client disconnected")
    except (SessionError, BadRequestError, SessionTimeoutError) as exc:
        session_log.warning("session ended with client error — {}", exc)
        try:
            await _send_error(websocket, exc)
            await websocket.close(code=1008)
        except WebSocketDisconnect:
            pass
    except Exception as exc:
        session_log.exception("unhandled session failure — {}", exc)
        try:
            await _send_error(
                websocket,
                SessionError(f"Session error: {exc}", code="SESSION_INTERNAL_ERROR"),
            )
            await websocket.close(code=1011)
        except WebSocketDisconnect:
            pass


async def _run_session(ws: WebSocket, session_id: str, session_log) -> None:
    """Internal session lifecycle: handshake → Gemini bridge → judge."""
    metrics = SessionMetrics(session_id=session_id)

    await ws.send_json({"type": "connected", "message": "Ready — send start message"})
    session_log.debug("sent connected frame")

    start_msg = await _receive_start(ws, session_log)
    resume_context = start_msg.resume_context
    job_description_context = start_msg.job_description_context
    candidate_name = start_msg.candidate_name
    candidate_email = start_msg.candidate_email
    company_id = start_msg.company_id

    memory_state = load_memory()
    system_instruction = build_system_prompt(memory_state, BASE_SYSTEM_INSTRUCTION)
    if resume_context:
        system_instruction = f"{system_instruction}\n\n{resume_context}"
    if job_description_context:
        system_instruction = f"{system_instruction}\n\n{job_description_context}"
    if company_id:
        company_context = get_company_context_block(company_id)
        if company_context:
            system_instruction = f"{system_instruction}\n\n{company_context}"

    session_log.info(
        "session config ready",
        resume_chars=len(resume_context),
        jd_chars=len(job_description_context),
        company_id=company_id or None,
        candidate_email=candidate_email or None,
        memory_turns=len(memory_state.get("raw_turns", [])),
    )

    session_transcript: list[tuple[str, str, str]] = []
    gemini_buf: list[str] = []
    user_buf: list[str] = []
    stop_event = asyncio.Event()
    user_audio_enabled = asyncio.Event()
    phase_flags: dict[str, bool] = {"skip_coding": False, "begin_coding": False}

    # Initialize Voice Guard (operates in mock if HF_TOKEN is missing)
    import os
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    is_mock = hf_token is None
    voice_guard = AIInterviewerVoiceGuard(hf_token=hf_token, mock=is_mock)
    if is_mock:
        voice_guard.enroll_speaker(None)
    guard_manager = SessionVoiceGuardManager(ws, voice_guard, stop_event)

    live_config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE_NAME)
            ),
            language_code=SPEECH_LANGUAGE_CODE,
        ),
        system_instruction=types.Content(parts=[types.Part(text=system_instruction)]),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )

    client = genai.Client(api_key=API_KEY)

    try:
        async with client.aio.live.connect(model=MODEL, config=live_config) as gemini:
            session_log.info(
                "gemini live connected",
                model=MODEL,
                voice=VOICE_NAME,
                language=SPEECH_LANGUAGE_CODE,
            )
            await ws.send_json({"type": "session_started"})
            session_log.info("sent session_started — triggering AI opening")

            browser_task = asyncio.create_task(
                _from_browser(
                    ws,
                    gemini,
                    stop_event,
                    user_audio_enabled,
                    metrics,
                    session_log,
                    phase_flags,
                    guard_manager,
                ),
                name=f"browser-{session_id}",
            )
            gemini_task = asyncio.create_task(
                _from_gemini(
                    ws,
                    gemini,
                    stop_event,
                    user_audio_enabled,
                    session_transcript,
                    gemini_buf,
                    user_buf,
                    metrics,
                    session_log,
                ),
                name=f"gemini-{session_id}",
            )

            await stop_event.wait()
            session_log.info("stop signalled — shutting down bridge", **metrics.model_dump())

            browser_task.cancel()
            gemini_task.cancel()
            await asyncio.gather(browser_task, gemini_task, return_exceptions=True)

            await _flush_partial_turn(ws, session_transcript, gemini_buf, user_buf)

    except Exception as exc:
        session_log.error("gemini session failed — {}", exc)
        raise SessionError(f"Session error: {exc}", code="GEMINI_SESSION_ERROR") from exc

    coding_submit: ClientCodingSubmitMessage | None = None
    coding_context = ""

    if not phase_flags.get("skip_coding"):
        problem_id = pick_coding_problem_id()
        await ws.send_json(
            {
                "type": "coding_round",
                "problem_id": problem_id,
                "time_limit_sec": CODING_ROUND_TIME_SEC,
            }
        )
        session_log.info(
            "coding round started",
            problem_id=problem_id,
            time_limit_sec=CODING_ROUND_TIME_SEC,
        )
        coding_submit = await _wait_coding_submit(
            ws,
            session_log,
            timeout_sec=CODING_ROUND_TIME_SEC + 180,
        )
        if coding_submit:
            coding_context = _append_coding_result(session_transcript, coding_submit)
            session_log.info(
                "coding submission received",
                passed=f"{coding_submit.passed_count}/{coding_submit.total_count}",
                timed_out=coding_submit.timed_out,
            )
        else:
            session_log.warning("coding round ended without submission")

    if session_transcript or coding_context:
        evaluation_context = "\n\n".join(
            block for block in (resume_context, job_description_context, coding_context) if block
        )
        report = await _run_judge(ws, session_transcript, evaluation_context, session_log)
        try:
            saved_path = save_interview_record(
                session_id=session_id,
                candidate_name=candidate_name,
                transcript=session_transcript,
                report=report,
                resume_context=resume_context,
                metrics=metrics.model_dump(),
            )
            session_log.info("interview archived", path=saved_path)
        except Exception as exc:
            session_log.error("failed to archive interview — {}", exc)

    await ws.send_json({"type": "session_ended"})
    session_log.info("session complete", **metrics.model_dump())
    try:
        await ws.close()
    except WebSocketDisconnect:
        pass


async def _receive_start(ws: WebSocket, session_log) -> ClientStartMessage:
    """Wait for the client's opening ``start`` message."""
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=60)
    except asyncio.TimeoutError as exc:
        session_log.warning("timeout waiting for start message")
        raise SessionTimeoutError("Timeout waiting for start") from exc

    try:
        payload = json.loads(raw)
        start = ClientStartMessage.model_validate(payload)
    except json.JSONDecodeError as exc:
        session_log.warning("invalid json on start — {}", exc)
        raise BadRequestError("First message must be valid JSON") from exc
    except ValidationError as exc:
        session_log.warning("invalid start payload — {}", exc)
        raise BadRequestError("First message must be {type: start}") from exc

    session_log.info(
        "start message received",
        resume_chars=len(start.resume_context),
        jd_chars=len(start.job_description_context),
    )
    return start


async def _send_final_transcript(ws: WebSocket, role: str, text: str) -> None:
    """Send complete turn text so the UI always has one full message."""
    cleaned = text.strip()
    if not cleaned or cleaned == "[inaudible]" or cleaned.startswith("[Audio"):
        return
    await ws.send_json({"type": role, "text": cleaned, "final": True})


def _join_transcript_buf(buf: list[str]) -> str:
    """Join Gemini transcription fragments (cumulative or incremental)."""
    if not buf:
        return ""
    if len(buf) == 1:
        return buf[0]
    # Cumulative stream: each chunk extends the previous → use the last chunk
    if buf[-1].startswith(buf[0][: min(len(buf[0]), 12)].strip()):
        return buf[-1]
    # Incremental fragments → join with spaces
    return " ".join(buf)


async def _trigger_ai_opening(gemini: Any, session_log) -> None:
    """Prompt Gemini to greet the candidate and speak first (no mic needed)."""
    session_log.info("sending opening prompt to Gemini")
    await gemini.send_client_content(
        turns=types.Content(
            role="user",
            parts=[
                types.Part(
                    text=(
                        f"The candidate has joined the interview. "
                        f"Begin now: introduce yourself as {INTERVIEWER_NAME}, "
                        "greet them warmly by name, and ask your first question."
                    )
                )
            ],
        ),
        turn_complete=True,
    )


async def _sync_gemini_transcript(
    ws: WebSocket,
    gemini_buf: list[str],
    last_sent: str,
) -> str:
    """Push only new transcript text, paired with an audio chunk."""
    current = _join_transcript_buf(gemini_buf)
    if not current or current == last_sent:
        return last_sent

    if last_sent and current.startswith(last_sent):
        delta = current[len(last_sent) :].lstrip()
        if not delta:
            return last_sent
        payload_text = delta
    else:
        payload_text = current

    await ws.send_json({"type": "transcript_gemini", "text": payload_text})
    return current


async def _flush_partial_turn(
    ws: WebSocket,
    session_transcript: list[tuple[str, str, str]],
    gemini_buf: list[str],
    user_buf: list[str],
) -> None:
    """Commit any in-progress turn when the client ends the session."""
    u_text = _join_transcript_buf(user_buf)
    a_text = _join_transcript_buf(gemini_buf)

    if u_text and u_text != "[inaudible]":
        await _send_final_transcript(ws, "transcript_user", u_text)
        session_transcript.append(("", "You", u_text))
    if a_text and not a_text.startswith("[Audio"):
        await _send_final_transcript(ws, "transcript_gemini", a_text)
        session_transcript.append(("", "Gemini", a_text))

    gemini_buf.clear()
    user_buf.clear()


def _append_coding_result(
    session_transcript: list[tuple[str, str, str]],
    submit: ClientCodingSubmitMessage,
) -> str:
    status = "timed out" if submit.timed_out else "submitted"
    summary = (
        f"Problem: {submit.problem_title or submit.problem_id}\n"
        f"Language: {submit.language}\n"
        f"Time taken: {submit.time_taken_sec}s ({status})\n"
        f"Tests passed: {submit.passed_count}/{submit.total_count}\n"
        f"All passed: {submit.all_passed}\n\n"
        f"Submitted code:\n{submit.source_code[:6000]}"
    )
    session_transcript.append(("", "Coding Submission", summary))
    return (
        "--- CODING ROUND SUBMISSION ---\n"
        "Evaluate the candidate's coding performance using this submission "
        "(correctness, approach, and code quality under time pressure).\n\n"
        f"{summary}\n"
        "--- END CODING ROUND ---"
    )


async def _wait_coding_submit(
    ws: WebSocket,
    session_log,
    timeout_sec: int,
) -> ClientCodingSubmitMessage | None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_sec

    while loop.time() < deadline:
        remaining = deadline - loop.time()
        try:
            raw = await asyncio.wait_for(ws.receive_text(), timeout=min(5.0, remaining))
        except asyncio.TimeoutError:
            continue
        except WebSocketDisconnect:
            session_log.info("client disconnected during coding round")
            return None

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if payload.get("type") != "coding_submit":
            continue

        try:
            return ClientCodingSubmitMessage.model_validate(payload)
        except ValidationError as exc:
            session_log.warning("invalid coding_submit payload — {}", exc)

    return None


async def _from_browser(
    ws: WebSocket,
    gemini: Any,
    stop_event: asyncio.Event,
    user_audio_enabled: asyncio.Event,
    metrics: SessionMetrics,
    session_log,
    phase_flags: dict[str, bool],
    guard_manager: SessionVoiceGuardManager,
) -> None:
    """Forward browser PCM chunks to Gemini Live."""
    try:
        while not stop_event.is_set():
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                session_log.warning("invalid json from client — {}", exc)
                continue

            msg_type = payload.get("type")

            if msg_type == "audio":
                if not user_audio_enabled.is_set():
                    continue
                audio = ClientAudioMessage.model_validate(payload)
                pcm = base64.b64decode(audio.data)
                
                # Feed incoming audio chunk to the voice guard manager
                asyncio.create_task(guard_manager.add_pcm_chunk(pcm))
                
                metrics.audio_chunks_in += 1
                metrics.audio_bytes_in += len(pcm)

                if metrics.audio_chunks_in == 1 or metrics.audio_chunks_in % 50 == 0:
                    session_log.debug(
                        "audio chunk received from browser",
                        chunk=metrics.audio_chunks_in,
                        bytes=len(pcm),
                    )

                await gemini.send_realtime_input(
                    audio=types.Blob(
                        data=pcm,
                        mime_type=f"audio/pcm;rate={INPUT_SAMPLE_RATE}",
                    )
                )
            elif msg_type == "begin_coding":
                ClientBeginCodingMessage.model_validate(payload)
                phase_flags["begin_coding"] = True
                session_log.info("begin_coding received — ending voice phase")
                stop_event.set()
            elif msg_type == "stop":
                stop = ClientStopMessage.model_validate(payload)
                if stop.skip_coding:
                    phase_flags["skip_coding"] = True
                    session_log.info("stop with skip_coding — skipping coding round")
                else:
                    session_log.info("stop message received from client")
                stop_event.set()
            else:
                session_log.warning("ignored unknown client message", msg_type=msg_type)

    except asyncio.CancelledError:
        session_log.debug("browser bridge task cancelled")
        raise
    except WebSocketDisconnect:
        session_log.info("browser websocket closed during audio bridge")
        stop_event.set()
    except ValidationError as exc:
        session_log.warning("invalid audio payload — {}", exc)
        stop_event.set()
    except Exception as exc:
        session_log.error("browser bridge failed — {}", exc)
        stop_event.set()
        # Do not re-raise — allow graceful session teardown + judge


async def _from_gemini(
    ws: WebSocket,
    gemini: Any,
    stop_event: asyncio.Event,
    user_audio_enabled: asyncio.Event,
    session_transcript: list[tuple[str, str, str]],
    gemini_buf: list[str],
    user_buf: list[str],
    metrics: SessionMetrics,
    session_log,
) -> None:
    """Forward Gemini audio and transcripts to the browser.

    ``gemini.receive()`` yields one model turn then stops (see google-genai
    live.py). We must call it again in a loop for multi-turn interviews.

    Audio is forwarded before transcript text so voice and captions stay in sync.
    Mic input is gated until the AI finishes its opening turn.
    """
    turn_count = 0
    turn_audio_started = False
    last_sent_gemini_tx = ""
    opening_sent = False

    try:
        while not stop_event.is_set():
            if not opening_sent:
                await _trigger_ai_opening(gemini, session_log)
                opening_sent = True

            session_log.debug("awaiting next gemini turn")
            async for response in gemini.receive():
                if stop_event.is_set():
                    break

                sc = getattr(response, "server_content", None)
                if not sc:
                    continue

                # 1. Audio first — transcript is only pushed after audio starts
                model_turn = getattr(sc, "model_turn", None)
                if model_turn and model_turn.parts and not stop_event.is_set():
                    for part in model_turn.parts:
                        if stop_event.is_set():
                            break
                        if part.inline_data and part.inline_data.data:
                            turn_audio_started = True
                            encoded = base64.b64encode(part.inline_data.data).decode()
                            metrics.audio_chunks_out += 1
                            if metrics.audio_chunks_out == 1 or metrics.audio_chunks_out % 25 == 0:
                                session_log.debug(
                                    "gemini audio chunk forwarded",
                                    chunk=metrics.audio_chunks_out,
                                    bytes=len(part.inline_data.data),
                                )
                            await ws.send_json({"type": "audio", "data": encoded})
                            last_sent_gemini_tx = await _sync_gemini_transcript(
                                ws, gemini_buf, last_sent_gemini_tx
                            )

                # 2. Gemini speech-to-text (buffered locally; sent with audio)
                ot = getattr(sc, "output_transcription", None)
                if ot:
                    txt = getattr(ot, "text", "") or ""
                    if txt.strip() and not stop_event.is_set():
                        cleaned = txt.strip()
                        gemini_buf.append(cleaned)
                        metrics.gemini_transcripts += 1
                        session_log.debug("gemini transcript fragment", text=cleaned[:120])
                        if turn_audio_started:
                            last_sent_gemini_tx = await _sync_gemini_transcript(
                                ws, gemini_buf, last_sent_gemini_tx
                            )

                # 3. User speech-to-text (only after mic is enabled)
                it = getattr(sc, "input_transcription", None)
                if it and user_audio_enabled.is_set():
                    txt = getattr(it, "text", "") or ""
                    if txt.strip() and not stop_event.is_set():
                        user_buf.append(txt.strip())
                        metrics.user_transcripts += 1
                        session_log.info("user transcript fragment", text=txt.strip()[:120])
                        await ws.send_json({"type": "transcript_user", "text": txt.strip()})

                if getattr(sc, "interrupted", False):
                    session_log.info("gemini interrupted (barge-in)")
                    await ws.send_json({"type": "interrupted"})

                if getattr(sc, "turn_complete", False) and not stop_event.is_set():
                    turn_count += 1
                    metrics.turns_completed = turn_count
                    mic_was_gated = not user_audio_enabled.is_set()

                    if turn_audio_started:
                        last_sent_gemini_tx = await _sync_gemini_transcript(
                            ws, gemini_buf, last_sent_gemini_tx
                        )

                    a_text = _join_transcript_buf(gemini_buf) or f"[Audio #{turn_count}]"
                    u_text = _join_transcript_buf(user_buf) or "[inaudible]"

                    if not mic_was_gated and u_text != "[inaudible]":
                        session_transcript.append(("", "You", u_text))
                    session_transcript.append(("", "Gemini", a_text))
                    session_log.info(
                        "turn complete",
                        turn=turn_count,
                        user_chars=len(u_text),
                        gemini_chars=len(a_text),
                    )

                    if not mic_was_gated and u_text != "[inaudible]":
                        await _send_final_transcript(ws, "transcript_user", u_text)
                    await _send_final_transcript(ws, "transcript_gemini", a_text)

                    gemini_buf.clear()
                    user_buf.clear()
                    turn_audio_started = False
                    last_sent_gemini_tx = ""

                    if mic_was_gated:
                        user_audio_enabled.set()
                        await ws.send_json({"type": "your_turn"})
                        session_log.info("AI opening complete — user mic enabled")

                    await ws.send_json({"type": "turn_complete"})

            session_log.debug("gemini turn ended — ready for next turn", turn=turn_count)

    except asyncio.CancelledError:
        session_log.debug("gemini bridge task cancelled")
        raise
    except WebSocketDisconnect:
        session_log.info("browser websocket closed during gemini stream")
        stop_event.set()
    except Exception as exc:
        if not stop_event.is_set():
            session_log.error("gemini stream failed — {}", exc)
            try:
                await _send_error(
                    ws,
                    SessionError(f"Stream: {exc}", code="GEMINI_STREAM_ERROR"),
                )
            except WebSocketDisconnect:
                pass
        stop_event.set()


async def _run_judge(
    ws: WebSocket,
    session_transcript: list[tuple[str, str, str]],
    resume_context: str,
    session_log,
) -> JudgeReport | None:
    """Run post-session LLM-as-Judge evaluation."""
    await ws.send_json({"type": "evaluating", "message": "AI judge is evaluating your interview…"})
    session_log.info("judge evaluation started", turns=len(session_transcript))

    try:
        loop = asyncio.get_running_loop()
        report = await loop.run_in_executor(
            None,
            run_judge,
            session_transcript,
            resume_context,
            GROQ_API_KEY,
        )
    except Exception as exc:
        session_log.error("judge evaluation failed — {}", exc)
        await _send_error(
            ws,
            SessionError(f"Judge error: {exc}", code="JUDGE_ERROR"),
        )
        return None

    if report is None:
        session_log.warning("judge returned no report")
        await _send_error(
            ws,
            SessionError("Judge returned no result", code="JUDGE_EMPTY"),
        )
        return None

    session_log.info(
        "judge evaluation complete",
        overall_score=report.overall_score,
        hire=report.hire_recommendation,
    )
    await ws.send_json(
        {
            "type": "scorecard",
            "report": {
                "dimensions": [
                    {"name": d.name, "score": d.score, "rationale": d.rationale}
                    for d in report.dimensions
                ],
                "overall_score": report.overall_score,
                "overall_verdict": report.overall_verdict,
                "strengths": report.strengths,
                "improvements": report.improvements,
                "hire_recommendation": report.hire_recommendation,
            },
        }
    )
    return report
