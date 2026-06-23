"""
services/job_description/context.py
───────────────────────────────────
Extract job description text from PDF/DOCX and format it for Gemini.
"""

from __future__ import annotations

from pathlib import Path

from services.resume.parser import extract_text


def extract_job_description_text(path: Path) -> str:
    """Return raw text from a PDF or DOCX job description file."""
    text = extract_text(path).strip()
    if not text:
        raise ValueError("Job description file appears empty.")
    return text


def build_job_description_system_block(raw_text: str, source_name: str = "") -> str:
    """Format JD text as a system-instruction block for the interviewer."""
    header = "--- JOB DESCRIPTION / ROLE CONTEXT ---"
    intro = (
        "The following is the job description for the role the candidate is interviewing for. "
        "Use it to shape your questions: required skills, responsibilities, seniority, "
        "and qualifications. Ask how the candidate's experience maps to this role. "
        "Probe gaps between the JD requirements and their background. "
        "Do not read the JD verbatim to the candidate."
    )
    source = f"Source file: {source_name}" if source_name else ""
    body = raw_text.strip()
    footer = "--- END OF JOB DESCRIPTION CONTEXT ---"

    parts = [header, intro]
    if source:
        parts.append(source)
    parts.extend(["", body, "", footer])
    return "\n".join(parts)


def load_job_description_context(path: Path | str | None) -> str:
    """Parse a JD file and return the formatted context block, or empty string."""
    if not path:
        return ""

    jd_path = Path(path)
    if not jd_path.exists():
        return ""

    try:
        text = extract_job_description_text(jd_path)
        return build_job_description_system_block(text, jd_path.name)
    except Exception:
        return ""
