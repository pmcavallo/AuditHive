"""Pydantic schemas for policy template endpoints."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class TemplateListItem(BaseModel):
    id: str
    name: str
    description: str
    use_case: str
    risk_level: str
    version: int
    regulatory_grounding: list[str]


class TemplateListResponse(BaseModel):
    templates: list[TemplateListItem]


class TemplateDetailResponse(BaseModel):
    id: str
    name: str
    description: str
    use_case: str
    risk_level: str
    version: int
    regulatory_grounding: list[str]
    config: dict


class TemplateApplyRequest(BaseModel):
    name: str | None = None
    customizations: dict = {}


class TemplateApplyResponse(BaseModel):
    policy_id: UUID
    template_id: str
    name: str
    config: dict
    message: str = "Policy created from template. Active on your next API call."
