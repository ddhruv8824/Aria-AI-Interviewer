"""Pydantic schemas for job description API endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class JobDescriptionContextResponse(BaseModel):
    """System-prompt context block returned by POST /job-description/context."""

    filename: str
    context_block: str
    char_count: int
