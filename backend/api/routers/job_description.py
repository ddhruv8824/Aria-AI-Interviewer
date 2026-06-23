"""
api/routers/job_description.py
──────────────────────────────
Job description upload → system-prompt context block.
"""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from api.models.job_description import JobDescriptionContextResponse
from services.job_description.context import (
    build_job_description_system_block,
    extract_job_description_text,
)

router = APIRouter(prefix="/job-description", tags=["Job Description"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _save_upload(upload: UploadFile) -> Path:
    ext = Path(upload.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Upload PDF, DOCX, or TXT.",
        )

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        tmp.write(upload.file.read())
        tmp.flush()
        return Path(tmp.name)
    finally:
        tmp.close()


@router.post(
    "/context",
    response_model=JobDescriptionContextResponse,
    summary="Generate job description system-prompt context",
)
async def job_description_context_endpoint(
    file: UploadFile = File(..., description="Job description — PDF, DOCX, or TXT"),
) -> JobDescriptionContextResponse:
    tmp_path = _save_upload(file)
    filename = file.filename or ""

    try:
        if tmp_path.suffix.lower() == ".txt":
            raw_text = tmp_path.read_text(encoding="utf-8", errors="replace").strip()
            if not raw_text:
                raise ValueError("Job description file appears empty.")
        else:
            raw_text = extract_job_description_text(tmp_path)

        context = build_job_description_system_block(raw_text, filename)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse job description: {exc}",
        ) from exc
    finally:
        os.unlink(tmp_path)

    return JobDescriptionContextResponse(
        filename=filename,
        context_block=context,
        char_count=len(raw_text),
    )
