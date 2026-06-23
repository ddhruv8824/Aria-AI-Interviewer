"""Pydantic models for WebSocket session messages."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ClientStartMessage(BaseModel):
    """Client message that begins a voice interview session."""

    type: Literal["start"]
    resume_context: str = ""
    job_description_context: str = ""
    candidate_name: str = ""
    candidate_email: str = ""
    company_id: str = ""


class ClientAudioMessage(BaseModel):
    """Client message carrying a base64-encoded PCM audio chunk."""

    type: Literal["audio"]
    data: str = Field(min_length=1)

    @field_validator("data")
    @classmethod
    def data_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("audio data must not be empty")
        return value


class ClientStopMessage(BaseModel):
    """Client message that skips coding and ends the session."""

    type: Literal["stop"]
    skip_coding: bool = False


class ClientBeginCodingMessage(BaseModel):
    """Client message that ends the voice phase and starts the coding round."""

    type: Literal["begin_coding"]


class ClientCodingSubmitMessage(BaseModel):
    """Client submission for the timed coding round."""

    type: Literal["coding_submit"]
    problem_id: str = ""
    problem_title: str = ""
    source_code: str = ""
    language: str = "python"
    passed_count: int = 0
    total_count: int = 0
    all_passed: bool = False
    time_taken_sec: int = 0
    timed_out: bool = False


class SessionMetrics(BaseModel):
    """Runtime counters for a single WebSocket session."""

    session_id: str
    audio_chunks_in: int = 0
    audio_bytes_in: int = 0
    audio_chunks_out: int = 0
    user_transcripts: int = 0
    gemini_transcripts: int = 0
    turns_completed: int = 0


class ServerErrorMessage(BaseModel):
    """Error payload sent to the browser."""

    type: Literal["error"] = "error"
    message: str
    code: str = "SESSION_ERROR"
    details: dict[str, Any] = Field(default_factory=dict)
