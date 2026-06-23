"""Pydantic schemas for platform / homepage API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CompanyOut(BaseModel):
    id: str
    name: str
    tagline: str
    color: str
    focus_areas: list[str] = Field(default_factory=list)


class CommunityQuestionOut(BaseModel):
    id: str
    company_id: str
    category: str
    question: str
    source: str
    created_at: str


class BlogOut(BaseModel):
    id: str
    company_id: str
    title: str
    author_label: str
    excerpt: str
    body: str
    created_at: str


class RegisterPracticeRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    company_id: str


class RegisterPracticeResponse(BaseModel):
    ok: bool = True
    registration_id: str
    email: str
    company_id: str
    company_name: str


class SubmitQuestionRequest(BaseModel):
    company_id: str
    question: str = Field(min_length=10, max_length=2000)
    category: str = "general"


class SubmitBlogRequest(BaseModel):
    company_id: str
    title: str = Field(min_length=5, max_length=200)
    body: str = Field(min_length=20, max_length=8000)
    author_label: str = "Anonymous"


class CompanyContextResponse(BaseModel):
    company_id: str
    company_name: str
    context_block: str
    question_count: int
    blog_count: int
