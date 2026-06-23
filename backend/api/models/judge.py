"""
api/models/judge.py
────────────────────
Pydantic schemas for the Judge service API endpoints.
"""

from __future__ import annotations
from typing import Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


# ── Request models ──────────────────────────────────────────

class TranscriptEntry(BaseModel):
    """A single line of the interview transcript."""
    timestamp: str = Field(
        default="",
        description="HH:MM:SS timestamp (optional — used for display only)"
    )
    role:  str = Field(description="'You' (candidate) or 'Gemini' (interviewer)")
    text:  str = Field(description="Spoken text for this turn")


class JudgeRequest(BaseModel):
    """Request body for POST /judge/evaluate."""
    transcript:     list[TranscriptEntry] = Field(
        description="Full ordered list of transcript entries"
    )
    resume_context: str = Field(
        default="",
        description="Optional resume context string (from /resume/context)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "transcript": [
                    {"timestamp": "10:00:01", "role": "You",    "text": "I built microservices at Stripe using Python and Kubernetes."},
                    {"timestamp": "10:00:15", "role": "Gemini", "text": "Can you walk me through the architecture?"},
                    {"timestamp": "10:00:30", "role": "You",    "text": "We used FastAPI for the APIs, Kafka for streaming, and deployed on GKE."},
                ],
                "resume_context": "Senior Software Engineer, 7 years. Skills: Python, Kubernetes, AWS."
            }
        }
    }


# ── Response models ─────────────────────────────────────────

class DimensionScoreOut(BaseModel):
    name:      str
    score:     int   = Field(ge=1, le=10)
    rationale: str


class JudgeReportResponse(BaseModel):
    """Full scorecard returned by POST /judge/evaluate."""
    dimensions:          list[DimensionScoreOut]
    overall_score:       float = Field(ge=0.0, le=10.0)
    overall_verdict:     str
    strengths:           list[str]
    improvements:        list[str]
    hire_recommendation: str   # "Strong Yes" | "Yes" | "Maybe" | "No"
    model_used:          str   = ""   # which Gemini model produced this score
