"""
api/models/memory.py
─────────────────────
Pydantic schemas for the Memory service API endpoints.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class TurnEntry(BaseModel):
    """A single conversation exchange stored in memory."""
    user:      str
    assistant: str


class MemoryStateResponse(BaseModel):
    """Current memory state returned by GET /memory."""
    summary:    str         = ""
    raw_turns:  list[TurnEntry] = Field(default_factory=list)
    turn_count: int         = 0


class MemoryPromptResponse(BaseModel):
    """Full system prompt with memory injected, returned by GET /memory/prompt."""
    system_prompt: str
    has_summary:   bool
    turn_count:    int


class MemoryClearResponse(BaseModel):
    """Confirmation returned by DELETE /memory."""
    cleared: bool
    message: str
