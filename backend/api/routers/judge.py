"""
api/routers/judge.py
─────────────────────
Judge service router.

Endpoints:
    POST /judge/evaluate    → submit interview transcript, receive scorecard
    GET  /judge/dimensions  → list the scoring dimensions and their weights
"""

import asyncio

from fastapi import APIRouter, HTTPException, status

from services.judge         import run_judge
from services.judge.evaluator import _DIMENSIONS, _WEIGHTS
from shared.config          import GROQ_API_KEY
from api.models.judge       import (
    JudgeRequest,
    JudgeReportResponse,
    DimensionScoreOut,
)
from pydantic import BaseModel

router = APIRouter(prefix="/judge", tags=["Judge"])


class DimensionInfo(BaseModel):
    name:        str
    weight:      float
    description: str


@router.get(
    "/dimensions",
    response_model=list[DimensionInfo],
    summary="List scoring dimensions",
    description="Returns the 5 evaluation dimensions used by the LLM-as-Judge, with weights.",
)
async def list_dimensions() -> list[DimensionInfo]:
    return [
        DimensionInfo(name=name, weight=weight, description=desc)
        for (name, desc), weight in zip(_DIMENSIONS, _WEIGHTS)
    ]


@router.post(
    "/evaluate",
    response_model=JudgeReportResponse,
    summary="Evaluate an interview session",
    description=(
        "Submit a full interview transcript and optional resume context. "
        "Gemini scores the candidate on 5 dimensions using the **LLM-as-Judge** "
        "pattern and returns a structured scorecard with an overall score, "
        "hire recommendation, strengths, and areas for improvement.\n\n"
        "The `transcript` field is an ordered list of `{timestamp, role, text}` objects. "
        "`role` must be `'You'` (candidate) or `'Gemini'` (interviewer)."
    ),
)
async def evaluate_interview(body: JudgeRequest) -> JudgeReportResponse:
    # Convert Pydantic models to the tuple format expected by run_judge
    transcript = [
        (entry.timestamp, entry.role, entry.text)
        for entry in body.transcript
    ]

    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcript is empty — provide at least one turn.",
        )

    # run_judge is synchronous (makes a Gemini REST call) — run in executor
    loop   = asyncio.get_event_loop()
    report = await loop.run_in_executor(
        None,
        run_judge,
        transcript,
        body.resume_context,
        GROQ_API_KEY,
    )

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Gemini judge returned no result. All configured models may be "
                "quota-exhausted. Please retry in a few minutes."
            ),
        )

    return JudgeReportResponse(
        dimensions=[
            DimensionScoreOut(
                name=d.name,
                score=d.score,
                rationale=d.rationale,
            )
            for d in report.dimensions
        ],
        overall_score=report.overall_score,
        overall_verdict=report.overall_verdict,
        strengths=report.strengths,
        improvements=report.improvements,
        hire_recommendation=report.hire_recommendation,
    )
