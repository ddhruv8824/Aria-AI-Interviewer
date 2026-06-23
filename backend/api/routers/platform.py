"""
api/routers/platform.py
───────────────────────
Homepage data: companies, community Q&A, blogs, email registration.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from api.models.platform import (
    BlogOut,
    CommunityQuestionOut,
    CompanyContextResponse,
    CompanyOut,
    RegisterPracticeRequest,
    RegisterPracticeResponse,
    SubmitBlogRequest,
    SubmitQuestionRequest,
)
from services.platform import (
    add_blog,
    add_community_question,
    get_company,
    get_company_context_block,
    list_blogs,
    list_community_questions,
    list_companies,
    register_practice_session,
)

router = APIRouter(prefix="/platform", tags=["Platform"])


@router.get("/companies", response_model=list[CompanyOut])
async def get_companies():
    return list_companies()


@router.get("/companies/{company_id}/questions", response_model=list[CommunityQuestionOut])
async def get_company_questions(company_id: str):
    if not get_company(company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    return list_community_questions(company_id)


@router.get("/companies/{company_id}/blogs", response_model=list[BlogOut])
async def get_company_blogs(company_id: str):
    if not get_company(company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    return list_blogs(company_id)


@router.get("/companies/{company_id}/context", response_model=CompanyContextResponse)
async def get_company_context(company_id: str):
    company = get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return CompanyContextResponse(
        company_id=company_id,
        company_name=company.get("name", company_id),
        context_block=get_company_context_block(company_id),
        question_count=len(list_community_questions(company_id)),
        blog_count=len(list_blogs(company_id)),
    )


@router.post("/register", response_model=RegisterPracticeResponse)
async def register_practice(body: RegisterPracticeRequest):
    try:
        entry = register_practice_session(email=body.email, company_id=body.company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    company = get_company(body.company_id) or {}
    return RegisterPracticeResponse(
        registration_id=entry["id"],
        email=entry["email"],
        company_id=entry["company_id"],
        company_name=company.get("name", body.company_id),
    )


@router.post("/questions", response_model=CommunityQuestionOut)
async def submit_question(body: SubmitQuestionRequest):
    try:
        return add_community_question(
            company_id=body.company_id,
            question=body.question,
            category=body.category,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/blogs", response_model=BlogOut)
async def submit_blog(body: SubmitBlogRequest):
    try:
        return add_blog(
            company_id=body.company_id,
            title=body.title,
            body=body.body,
            author_label=body.author_label,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/questions", response_model=list[CommunityQuestionOut])
async def get_all_questions(company_id: str | None = None):
    return list_community_questions(company_id)


@router.get("/blogs", response_model=list[BlogOut])
async def get_all_blogs(company_id: str | None = None):
    return list_blogs(company_id)
