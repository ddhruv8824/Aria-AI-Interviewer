"""
api/models/resume.py
─────────────────────
Pydantic schemas for the Resume service API endpoints.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class ContactInfoOut(BaseModel):
    name:     Optional[str] = None
    email:    Optional[str] = None
    phone:    Optional[str] = None
    linkedin: Optional[str] = None
    github:   Optional[str] = None
    location: Optional[str] = None
    website:  Optional[str] = None


class ExperienceOut(BaseModel):
    company:    Optional[str] = None
    title:      Optional[str] = None
    start_date: Optional[str] = None
    end_date:   Optional[str] = None
    location:   Optional[str] = None
    bullets:    list[str]     = Field(default_factory=list)


class EducationOut(BaseModel):
    institution:     Optional[str] = None
    degree:          Optional[str] = None
    field_of_study:  Optional[str] = None
    graduation_date: Optional[str] = None
    gpa:             Optional[str] = None


class ResumeParseResponse(BaseModel):
    """Full structured resume data returned by POST /resume/parse."""
    source_file:    str
    contact:        ContactInfoOut
    summary:        Optional[str]  = None
    skills:         list[str]      = Field(default_factory=list)
    experience:     list[ExperienceOut] = Field(default_factory=list)
    education:      list[EducationOut]  = Field(default_factory=list)
    certifications: list[str]      = Field(default_factory=list)
    languages:      list[str]      = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ResumeContextResponse(BaseModel):
    """System-prompt context block returned by POST /resume/context."""
    filename:       str
    context_block:  str
    candidate_name: Optional[str] = None
    skill_count:    int
    role_count:     int
    education_count: int
