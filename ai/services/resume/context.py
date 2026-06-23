"""
services/resume/context.py
───────────────────────────
Loads and embeds resume data into the voice assistant's system prompt.

Workflow
────────
1. Parse the resume file (PDF or DOCX) with services.resume.parser.parse_resume()
2. Convert the structured ResumeData into a rich natural-language block
3. Return that block so core.assistant injects it into the Gemini system
   instruction alongside the existing memory context

Public API
──────────
    load_resume_context(path)              -> str
    build_resume_system_block(resume_data) -> str
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from services.resume.parser import parse_resume, ResumeData
from shared.ui import print_status, print_error, Colors


# ──────────────────────────────────────────────
# Public helpers
# ──────────────────────────────────────────────

def load_resume_context(path: Optional[str | Path]) -> str:
    """
    Parse the resume at *path* and return a formatted context string suitable
    for embedding in a Gemini system instruction.

    Returns an empty string if the path is None/empty, the file doesn't
    exist, or parsing fails.
    """
    if not path:
        return ""

    resume_path = Path(path)
    if not resume_path.exists():
        print_error(f"Resume file not found: {resume_path}")
        return ""

    try:
        print_status(f"Parsing resume: {resume_path.name} …", Colors.CYAN)
        data  = parse_resume(resume_path, original_filename=resume_path.name)
        block = build_resume_system_block(data)
        print_status(
            f"Resume loaded ✓  ({resume_path.name}  —  "
            f"{len(data.skills)} skills, {len(data.experience)} roles, "
            f"{len(data.education)} education entries)",
            Colors.GREEN,
        )
        return block
    except Exception as exc:
        print_error(f"Failed to parse resume: {exc}")
        return ""


def build_resume_system_block(data: ResumeData) -> str:
    """
    Convert a parsed ResumeData object into a structured natural-language block
    that can be embedded inside a Gemini system instruction.
    """
    lines: list[str] = []

    lines.append("--- RESUME / CANDIDATE CONTEXT ---")
    lines.append(
        "The following is structured information extracted from the candidate's resume. "
        "Use it to ask specific, targeted interview questions. Reference exact job "
        "titles, company names, technologies, certifications, and achievements when "
        "formulating each question. The candidate cannot see this data — surface it "
        "naturally through your questions. Do not read the data verbatim."
    )
    lines.append("")

    # ── Contact ──────────────────────────────────
    c = data.contact
    if c.name:     lines.append(f"Candidate name: {c.name}")
    if c.email:    lines.append(f"Email: {c.email}")
    if c.phone:    lines.append(f"Phone: {c.phone}")
    if c.linkedin: lines.append(f"LinkedIn: {c.linkedin}")
    if c.github:   lines.append(f"GitHub: {c.github}")
    if c.location: lines.append(f"Location: {c.location}")

    # ── Summary ───────────────────────────────────
    if data.summary:
        lines.append("")
        lines.append(f"Professional summary: {data.summary}")

    # ── Skills ────────────────────────────────────
    if data.skills:
        lines.append("")
        lines.append(f"Skills ({len(data.skills)} total): " + ", ".join(data.skills))

    # ── Experience ────────────────────────────────
    if data.experience:
        lines.append("")
        lines.append(f"Work experience ({len(data.experience)} roles):")
        for exp in data.experience:
            title   = exp.title   or "Unknown Title"
            company = exp.company or "Unknown Company"
            start   = exp.start_date or "?"
            end     = exp.end_date   or "present"
            header  = f"  • {title} at {company}  ({start} – {end})"
            if exp.location:
                header += f"  [{exp.location}]"
            lines.append(header)
            for bullet in exp.bullets[:5]:
                lines.append(f"      – {bullet}")

    # ── Education ─────────────────────────────────
    if data.education:
        lines.append("")
        lines.append(f"Education ({len(data.education)} entries):")
        for edu in data.education:
            degree  = edu.degree          or "Degree unknown"
            inst    = edu.institution     or "Institution unknown"
            grad    = edu.graduation_date or "—"
            gpa_str = f"  GPA: {edu.gpa}" if edu.gpa else ""
            lines.append(f"  • {degree}  |  {inst}  |  Graduated: {grad}{gpa_str}")

    # ── Certifications ────────────────────────────
    if data.certifications:
        lines.append("")
        lines.append("Certifications:")
        for cert in data.certifications:
            lines.append(f"  • {cert}")

    # ── Languages ─────────────────────────────────
    if data.languages:
        lines.append("")
        lines.append("Languages spoken: " + ", ".join(data.languages))

    lines.append("")
    lines.append("--- END OF RESUME CONTEXT ---")

    return "\n".join(lines)
