"""
services/memory/memory.py
──────────────────────────
LangGraph-powered persistent memory layer for the Gemini Live Voice
Interview Assistant.

Architecture
────────────
Every completed exchange (user turn + assistant turn) is fed into a compiled
LangGraph graph.  The graph has three nodes:

    add_turn   → appends the new exchange to the raw_turns buffer
         ↓ conditional
    summarise  → calls the Gemini text model to condense raw_turns into
                 a rolling summary, then clears the buffer  (if triggered)
    persist    → always runs last; writes state to memory/memory.json

On startup the assistant loads the JSON file, injects the summary + recent
raw turns into the system prompt, and Gemini instantly "remembers" prior
sessions without any special API.

Public API
──────────
    load_memory()                               → MemoryState
    build_memory_graph()                        → compiled LangGraph app
    build_system_prompt(state, base_instruction) → str
"""

import json
import os
from typing import TypedDict, List, Optional

# pyrefly: ignore [missing-import]
from langgraph.graph import StateGraph, END

from shared.config import API_KEY, MEMORY_DIR, MEMORY_FILE
from shared.ui import print_status, print_error, Colors


# ──────────────────────────────────────────────
# State schema
# ──────────────────────────────────────────────

class MemoryState(TypedDict):
    """
    The single state object that flows through every node of the memory graph.

    summary          – Rolling prose summary of all past conversations.
    raw_turns        – Recent exchanges not yet folded into the summary.
                       Each entry: {"user": str, "assistant": str}
    new_turn         – The exchange just completed; consumed by node_add_turn.
    should_summarise – Set by node_add_turn; read by the conditional edge.
    """
    summary:          str
    raw_turns:        List[dict]
    new_turn:         Optional[dict]
    should_summarise: bool


# ──────────────────────────────────────────────
# Disk I/O
# ──────────────────────────────────────────────

def load_memory() -> MemoryState:
    """
    Load persisted memory from disk.
    Returns a blank MemoryState if the file does not exist or is corrupt.
    """
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return MemoryState(
                summary=data.get("summary", ""),
                raw_turns=data.get("raw_turns", []),
                new_turn=None,
                should_summarise=False,
            )
        except Exception:
            pass   # fall through to blank state

    return MemoryState(
        summary="",
        raw_turns=[],
        new_turn=None,
        should_summarise=False,
    )


def _save_memory(state: MemoryState) -> None:
    """Write summary + raw_turns to disk (internal use only)."""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"summary": state["summary"], "raw_turns": state["raw_turns"]},
            f,
            ensure_ascii=False,
            indent=2,
        )


# ──────────────────────────────────────────────
# Graph nodes
# ──────────────────────────────────────────────

def node_add_turn(state: MemoryState) -> MemoryState:
    """
    Consume new_turn and push it onto raw_turns.
    """
    new_turn = state.get("new_turn")
    if not new_turn:
        return state

    raw_turns = list(state["raw_turns"])
    raw_turns.append(new_turn)

    return MemoryState(
        summary=state["summary"],
        raw_turns=raw_turns,
        new_turn=None,
        should_summarise=False,
    )


def node_summarise(state: MemoryState) -> MemoryState:
    """
    Condense raw_turns into the running summary via the Gemini text model.
    Called only when should_summarise is True (buffer is full).
    Clears raw_turns on success; keeps them on API failure to avoid data loss.
    """
    from google import genai  # type: ignore

    client     = genai.Client(api_key=API_KEY)
    turns_text = "\n".join(
        f"User: {t['user']}\nAssistant: {t['assistant']}"
        for t in state["raw_turns"]
    )
    existing = state["summary"]

    if existing:
        prompt = (
            "You are a memory assistant. Below is an existing conversation summary "
            "and new conversation turns. Merge them into a single concise summary "
            "(max 300 words) capturing key facts, preferences, and topics discussed.\n\n"
            f"EXISTING SUMMARY:\n{existing}\n\n"
            f"NEW TURNS:\n{turns_text}\n\n"
            "Write only the updated summary, nothing else."
        )
    else:
        prompt = (
            "Summarise the following conversation in under 200 words, "
            "capturing key facts, user preferences, and topics discussed.\n\n"
            f"{turns_text}\n\nWrite only the summary, nothing else."
        )

    try:
        response    = client.models.generate_content(contents=prompt)
        new_summary = response.text.strip()
        print_status(
            f"Memory summarised ({len(state['raw_turns'])} turns condensed)",
            Colors.CYAN,
        )
        cleared_turns: List[dict] = []
    except Exception as e:
        print_error(f"Summarisation failed: {e}")
        new_summary   = existing
        cleared_turns = list(state["raw_turns"])

    return MemoryState(
        summary=new_summary,
        raw_turns=cleared_turns,
        new_turn=None,
        should_summarise=False,
    )


def node_persist(state: MemoryState) -> MemoryState:
    """Always-last node: write the current state to disk."""
    _save_memory(state)
    return state


# ──────────────────────────────────────────────
# Conditional edge router
# ──────────────────────────────────────────────

def _route_after_add(state: MemoryState) -> str:
    return "summarise" if state.get("should_summarise") else "persist"


# ──────────────────────────────────────────────
# Graph factory
# ──────────────────────────────────────────────

def build_memory_graph():
    """
    Compile and return the LangGraph memory graph.

    Flow:
        add_turn → (conditional) → summarise → persist → END
                               └──────────→ persist → END
    """
    g = StateGraph(MemoryState)

    g.add_node("add_turn",  node_add_turn)
    g.add_node("summarise", node_summarise)
    g.add_node("persist",   node_persist)

    g.set_entry_point("add_turn")
    g.add_conditional_edges(
        "add_turn",
        _route_after_add,
        {"summarise": "summarise", "persist": "persist"},
    )
    g.add_edge("summarise", "persist")
    g.add_edge("persist",   END)

    return g.compile()


# ──────────────────────────────────────────────
# System-prompt builder
# ──────────────────────────────────────────────

def build_system_prompt(state: MemoryState, base_instruction: str) -> str:
    """
    Inject the persisted memory into the base system instruction.

    The summary (compressed history) and the most recent 4 raw turns
    (verbatim recency) are appended under clearly labelled headings so
    Gemini can use them naturally without being told it has a file.
    """
    parts     = [base_instruction]
    summary   = state.get("summary", "")
    raw_turns = state.get("raw_turns", [])

    if summary:
        parts.append(
            f"\n\n--- MEMORY FROM PREVIOUS CONVERSATIONS ---\n{summary}"
        )

    if raw_turns:
        recent_lines: List[str] = []
        for t in raw_turns[-4:]:   # last 4 turns for recency context
            recent_lines.append(f"User: {t['user']}")
            recent_lines.append(f"Assistant: {t['assistant']}")
        parts.append(
            "\n\n--- RECENT EXCHANGES ---\n" + "\n".join(recent_lines)
        )

    if summary or raw_turns:
        parts.append(
            "\n\nUse the above memory naturally in conversation when relevant. "
            "Do not mention that you have a memory file or that you are reading from storage."
        )

    return "\n".join(parts)
