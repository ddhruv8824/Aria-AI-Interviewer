"""
services/platform/store.py
──────────────────────────
JSON-backed store for company practice content (homepage + AI context).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from shared.config import PLATFORM_DIR


def _path(name: str) -> str:
    return os.path.join(PLATFORM_DIR, name)


def _read_json(name: str, default: Any) -> Any:
    path = _path(name)
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(name: str, data: Any) -> None:
    os.makedirs(PLATFORM_DIR, exist_ok=True)
    with open(_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_companies() -> list[dict[str, Any]]:
    return _read_json("companies.json", [])


def get_company(company_id: str) -> Optional[dict[str, Any]]:
    for company in list_companies():
        if company.get("id") == company_id:
            return company
    return None


def list_community_questions(company_id: str | None = None) -> list[dict[str, Any]]:
    rows = _read_json("community_questions.json", [])
    if company_id:
        rows = [r for r in rows if r.get("company_id") == company_id]
    return sorted(rows, key=lambda r: r.get("created_at", ""), reverse=True)


def list_blogs(company_id: str | None = None) -> list[dict[str, Any]]:
    rows = _read_json("blogs.json", [])
    if company_id:
        rows = [r for r in rows if r.get("company_id") == company_id]
    return sorted(rows, key=lambda r: r.get("created_at", ""), reverse=True)


def add_community_question(
    *,
    company_id: str,
    question: str,
    category: str = "general",
) -> dict[str, Any]:
    if not get_company(company_id):
        raise ValueError(f"Unknown company: {company_id}")

    entry = {
        "id": f"q_{uuid.uuid4().hex[:8]}",
        "company_id": company_id,
        "category": category.strip() or "general",
        "question": question.strip(),
        "source": "community",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    rows = _read_json("community_questions.json", [])
    rows.append(entry)
    _write_json("community_questions.json", rows)
    return entry


def add_blog(
    *,
    company_id: str,
    title: str,
    body: str,
    author_label: str = "Anonymous",
) -> dict[str, Any]:
    if not get_company(company_id):
        raise ValueError(f"Unknown company: {company_id}")

    excerpt = body.strip()[:220] + ("…" if len(body.strip()) > 220 else "")
    entry = {
        "id": f"b_{uuid.uuid4().hex[:8]}",
        "company_id": company_id,
        "title": title.strip(),
        "author_label": author_label.strip() or "Anonymous",
        "excerpt": excerpt,
        "body": body.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    rows = _read_json("blogs.json", [])
    rows.append(entry)
    _write_json("blogs.json", rows)
    return entry


def register_practice_session(*, email: str, company_id: str) -> dict[str, Any]:
    email_clean = email.strip().lower()
    if "@" not in email_clean or "." not in email_clean.split("@")[-1]:
        raise ValueError("Invalid email address")
    if not get_company(company_id):
        raise ValueError(f"Unknown company: {company_id}")

    entry = {
        "id": uuid.uuid4().hex[:12],
        "email": email_clean,
        "company_id": company_id,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    rows = _read_json("registrations.json", [])
    rows.append(entry)
    _write_json("registrations.json", rows)
    return entry


def get_company_context_block(company_id: str) -> str:
    """Build AI system-prompt block from company profile + community data."""
    company = get_company(company_id)
    if not company:
        return ""

    questions = list_community_questions(company_id)[:12]
    blogs = list_blogs(company_id)[:5]

    lines = [
        "--- COMPANY INTERVIEW CONTEXT ---",
        f"Target company: {company.get('name', company_id)}",
        f"Interview style: {company.get('tagline', '')}",
    ]
    focus = company.get("focus_areas") or []
    if focus:
        lines.append("Focus areas: " + ", ".join(focus))

    if questions:
        lines.append("")
        lines.append("Community-reported questions (use as inspiration — do not claim they are official):")
        for q in questions:
            cat = q.get("category", "general")
            lines.append(f"  • [{cat}] {q.get('question', '')}")

    if blogs:
        lines.append("")
        lines.append("Recent candidate experiences (summarize themes, do not read verbatim):")
        for b in blogs:
            lines.append(f"  • {b.get('title', '')}: {b.get('excerpt', '')}")

    lines.append("")
    lines.append(
        "Tailor verbal and coding questions to this company's style. Reference their focus areas "
        "and realistic question patterns above."
    )
    lines.append("--- END COMPANY CONTEXT ---")
    return "\n".join(lines)
