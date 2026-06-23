"""
api/routers/memory.py
──────────────────────
Memory service router.

Endpoints:
    GET    /memory          → retrieve the current persisted memory state
    DELETE /memory          → clear memory (wipe summary + all raw turns)
    GET    /memory/prompt   → get the full system prompt with memory injected
"""

import json
import os

from fastapi import APIRouter, HTTPException, status

from services.memory        import load_memory, build_system_prompt
from shared.config          import BASE_SYSTEM_INSTRUCTION, MEMORY_FILE, MEMORY_DIR
from api.models.memory      import MemoryStateResponse, MemoryPromptResponse, MemoryClearResponse, TurnEntry

router = APIRouter(prefix="/memory", tags=["Memory"])


@router.get(
    "",
    response_model=MemoryStateResponse,
    summary="Get current memory state",
    description=(
        "Returns the persisted conversation memory: a rolling summary of all "
        "past sessions and the most recent raw turn exchanges."
    ),
)
async def get_memory() -> MemoryStateResponse:
    state = load_memory()
    return MemoryStateResponse(
        summary=state.get("summary", ""),
        raw_turns=[
            TurnEntry(user=t["user"], assistant=t["assistant"])
            for t in state.get("raw_turns", [])
        ],
        turn_count=len(state.get("raw_turns", [])),
    )


@router.get(
    "/prompt",
    response_model=MemoryPromptResponse,
    summary="Get system prompt with memory injected",
    description=(
        "Returns the full system instruction that would be sent to Gemini at "
        "session start — base instruction + injected memory context."
    ),
)
async def get_memory_prompt() -> MemoryPromptResponse:
    state  = load_memory()
    prompt = build_system_prompt(state, BASE_SYSTEM_INSTRUCTION)
    return MemoryPromptResponse(
        system_prompt=prompt,
        has_summary=bool(state.get("summary", "")),
        turn_count=len(state.get("raw_turns", [])),
    )


@router.delete(
    "",
    response_model=MemoryClearResponse,
    summary="Clear all memory",
    description=(
        "Permanently wipes the persisted memory file (summary and all raw turns). "
        "The next voice session will start with a blank slate."
    ),
)
async def clear_memory() -> MemoryClearResponse:
    if not os.path.exists(MEMORY_FILE):
        return MemoryClearResponse(
            cleared=False,
            message="Memory file does not exist — nothing to clear.",
        )

    try:
        os.makedirs(MEMORY_DIR, exist_ok=True)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"summary": "", "raw_turns": []}, f)
        return MemoryClearResponse(
            cleared=True,
            message="Memory cleared successfully.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear memory: {exc}",
        )
