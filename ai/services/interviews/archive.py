"""
services/interviews/archive.py
──────────────────────────────
Persist completed web interview sessions to disk (JSON).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

from services.judge import JudgeReport
from shared.config import INTERVIEWER_NAME, INTERVIEWS_DIR, MODEL, VOICE_NAME


def extract_candidate_name(resume_context: str, explicit: str = "") -> str:
    """Resolve display name from start payload or resume context block."""
    if explicit and explicit.strip():
        return explicit.strip()

    match = re.search(r"^Candidate name:\s*(.+)$", resume_context or "", re.MULTILINE)
    if match:
        return match.group(1).strip()

    return "Unknown Candidate"


def _slug(text: str, max_len: int = 48) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", text.lower())
    cleaned = re.sub(r"[\s_]+", "-", cleaned).strip("-")
    return (cleaned[:max_len] if cleaned else "candidate")


def report_to_dict(report: JudgeReport) -> dict[str, Any]:
    return {
        "overall_score": report.overall_score,
        "overall_verdict": report.overall_verdict,
        "hire_recommendation": report.hire_recommendation,
        "dimensions": [
            {"name": d.name, "score": d.score, "rationale": d.rationale}
            for d in report.dimensions
        ],
        "strengths": list(report.strengths),
        "improvements": list(report.improvements),
    }


def _transcript_to_list(transcript: list[tuple[str, str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for timestamp, role, text in transcript:
        cleaned = text.strip()
        if not cleaned or cleaned in ("[inaudible]", "[interrupted]"):
            continue
        if cleaned.startswith("[Audio"):
            continue
        rows.append(
            {
                "timestamp": timestamp,
                "role": role,
                "text": cleaned,
            }
        )
    return rows


def save_interview_record(
    *,
    session_id: str,
    candidate_name: str,
    transcript: list[tuple[str, str, str]],
    report: Optional[JudgeReport],
    resume_context: str = "",
    metrics: Optional[dict[str, Any]] = None,
) -> str:
    """
    Write one interview JSON file and append a summary row to index.json.

    Returns the path to the saved record file.
    """
    if not transcript:
        raise ValueError("Cannot archive an empty interview transcript")

    os.makedirs(INTERVIEWS_DIR, exist_ok=True)
    now = datetime.now(timezone.utc)
    resolved_name = extract_candidate_name(resume_context, candidate_name)

    record: dict[str, Any] = {
        "session_id": session_id,
        "candidate_name": resolved_name,
        "interviewed_at": now.isoformat(),
        "interviewer": INTERVIEWER_NAME,
        "model": MODEL,
        "voice": VOICE_NAME,
        "transcript": _transcript_to_list(transcript),
        "result": report_to_dict(report) if report else None,
        "metrics": metrics or {},
    }

    filename = (
        f"{now.strftime('%Y%m%d_%H%M%S')}_{session_id}_{_slug(resolved_name)}.json"
    )
    filepath = os.path.join(INTERVIEWS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    index_path = os.path.join(INTERVIEWS_DIR, "index.json")
    index: list[dict[str, Any]] = []
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, list):
                index = loaded
        except (json.JSONDecodeError, OSError):
            index = []

    index.append(
        {
            "session_id": session_id,
            "candidate_name": resolved_name,
            "interviewed_at": record["interviewed_at"],
            "file": filename,
            "overall_score": record["result"]["overall_score"] if record["result"] else None,
            "hire_recommendation": (
                record["result"]["hire_recommendation"] if record["result"] else None
            ),
        }
    )

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    return filepath
