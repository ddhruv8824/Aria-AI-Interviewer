"""
api/routers/resume.py
──────────────────────
Resume service router.

Endpoints:
    POST /resume/parse      → upload a PDF/DOCX, receive structured JSON data
    POST /resume/context    → upload a PDF/DOCX, receive the system-prompt context block
"""

import tempfile
import os
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from services.resume        import parse_resume, load_resume_context
from services.resume.context import build_resume_system_block
from api.models.resume      import ResumeParseResponse, ResumeContextResponse, ContactInfoOut, ExperienceOut, EducationOut

router = APIRouter(prefix="/resume", tags=["Resume"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def _save_upload(upload: UploadFile) -> Path:
    """
    Save the uploaded file to a temporary location and return the path.
    Raises HTTPException 400 if the file type is not supported.
    """
    ext = Path(upload.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Upload a PDF or DOCX file.",
        )

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        tmp.write(upload.file.read())
        tmp.flush()
        return Path(tmp.name)
    finally:
        tmp.close()


@router.post(
    "/parse",
    response_model=ResumeParseResponse,
    summary="Parse a resume file",
    description=(
        "Upload a **PDF** or **DOCX** resume and receive the fully structured "
        "candidate data as JSON: contact info, skills, experience, education, "
        "certifications, and languages."
    ),
)
async def parse_resume_endpoint(
    file: UploadFile = File(..., description="Resume file — PDF or DOCX"),
) -> ResumeParseResponse:
    tmp_path = _save_upload(file)

    try:
        data = parse_resume(tmp_path, original_filename=file.filename)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse resume: {exc}",
        )
    finally:
        os.unlink(tmp_path)

    return ResumeParseResponse(
        source_file=file.filename or "",
        contact=ContactInfoOut(
            name=data.contact.name,
            email=data.contact.email,
            phone=data.contact.phone,
            linkedin=data.contact.linkedin,
            github=data.contact.github,
            location=data.contact.location,
            website=data.contact.website,
        ),
        summary=data.summary,
        skills=data.skills,
        experience=[
            ExperienceOut(
                company=exp.company,
                title=exp.title,
                start_date=exp.start_date,
                end_date=exp.end_date,
                location=exp.location,
                bullets=exp.bullets,
            )
            for exp in data.experience
        ],
        education=[
            EducationOut(
                institution=edu.institution,
                degree=edu.degree,
                field_of_study=edu.field_of_study,
                graduation_date=edu.graduation_date,
                gpa=edu.gpa,
            )
            for edu in data.education
        ],
        certifications=data.certifications,
        languages=data.languages,
    )


@router.post(
    "/context",
    response_model=ResumeContextResponse,
    summary="Generate resume system-prompt context",
    description=(
        "Upload a **PDF** or **DOCX** resume and receive a pre-formatted context "
        "block ready to be embedded in a Gemini system instruction. This is the "
        "same block the voice assistant injects at session start."
    ),
)
async def resume_context_endpoint(
    file: UploadFile = File(..., description="Resume file — PDF or DOCX"),
) -> ResumeContextResponse:
    tmp_path = _save_upload(file)

    try:
        data    = parse_resume(tmp_path, original_filename=file.filename)
        context = build_resume_system_block(data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to build resume context: {exc}",
        )
    finally:
        os.unlink(tmp_path)

    return ResumeContextResponse(
        filename=file.filename or "",
        context_block=context,
        candidate_name=data.contact.name,
        skill_count=len(data.skills),
        role_count=len(data.experience),
        education_count=len(data.education),
    )
