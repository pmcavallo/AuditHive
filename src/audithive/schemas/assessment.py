"""Pydantic schemas for profile, assessment, gaps, and four questions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# ── Profile ────────────────────────────────────────────────────────

class ProfileCreate(BaseModel):
    ai_use_cases: list[str]
    audience_types: list[str]
    industry: str
    jurisdictions: list[str]
    ai_features_enabled: bool = False


class ProfileResponse(BaseModel):
    profile_id: UUID
    ai_use_cases: list[str]
    audience_types: list[str]
    industry: str
    jurisdictions: list[str]
    ai_features_enabled: bool = False
    ai_features_disclosure: str | None = None
    message: str = "Profile saved. Run GET /v1/assessment to see your governance gaps."

    model_config = {"from_attributes": True}


# ── Assessment ─────────────────────────────────────────────────────

class ApplicableRegulation(BaseModel):
    regulation: str
    jurisdiction: str
    why: str


class RequiredControl(BaseModel):
    control: str
    required_by: list[str]
    status: str  # "covered" | "missing"


class MissingControl(BaseModel):
    control: str
    required_by: list[str]
    fix: str
    effort: str


class FourQuestionStatus(BaseModel):
    answered: bool
    answer: str | None = None
    recommendation: str | None = None


class AssessmentResponse(BaseModel):
    assessment_id: UUID
    coverage_score: float
    maturity_level: str
    applicable_regulations: list[ApplicableRegulation]
    required_controls: list[RequiredControl]
    missing_controls: list[MissingControl]
    examiner_questions: list[str]
    four_questions: dict
    recommendations: list[str]


# ── Gaps ───────────────────────────────────────────────────────────

class Gap(BaseModel):
    gap_type: str
    description: str
    risk: str
    fix: str
    effort: str


class GapsResponse(BaseModel):
    gaps: list[Gap]
    gap_count: int
    overall_alignment: str


# ── Four Questions ─────────────────────────────────────────────────

class FourQuestionsRequest(BaseModel):
    purpose: str | None = None
    working: str | None = None
    failure: str | None = None
    accountability: str | None = None


class QuestionAssessment(BaseModel):
    answered: bool
    answer: str | None = None
    assessment: str | None = None
    recommendation: str | None = None
    gap: str | None = None


class FourQuestionsResponse(BaseModel):
    maturity_level: str
    maturity_score: int
    questions: dict[str, QuestionAssessment]
    maturity_breakdown: str
