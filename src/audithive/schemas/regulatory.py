"""Pydantic schemas for regulatory update and impact endpoints."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class RegulatoryUpdateItem(BaseModel):
    id: UUID
    title: str
    summary: str
    jurisdiction: str
    severity: str
    enforcement_date: date | None
    deadline: date | None
    update_type: str
    source_name: str | None

    model_config = {"from_attributes": True}


class RegulatoryUpdateListResponse(BaseModel):
    updates: list[RegulatoryUpdateItem]


class RegulatoryUpdateCreate(BaseModel):
    title: str
    summary: str
    regulation_short: str | None = None
    regulation_name: str | None = None
    update_type: str
    jurisdiction: str
    industries: list[str] = ["any"]
    use_cases: list[str] = ["any"]
    audiences: list[str] = ["any"]
    required_actions: list[dict] = []
    affected_controls: list[str] = []
    severity: str = "medium"
    effective_date: date | None = None
    enforcement_date: date | None = None
    deadline: date | None = None
    source_name: str | None = None
    source_url: str | None = None


class ImpactItem(BaseModel):
    id: UUID
    regulatory_update: RegulatoryUpdateItem
    impact_level: str
    is_affected: bool
    reasons: list[str]
    controls_in_place: list[dict]
    controls_missing: list[dict]
    required_actions: list[dict]
    days_until_deadline: int | None
    acknowledged: bool


class ImpactSummary(BaseModel):
    total_affecting: int
    critical: int
    high: int
    medium: int
    actions_required: int
    next_deadline: str | None
    next_deadline_regulation: str | None


class ImpactListResponse(BaseModel):
    impacts: list[ImpactItem]
    summary: ImpactSummary


class TimelineItem(BaseModel):
    date: str
    regulation: str
    impact_level: str
    actions_required: int
    actions_completed: int
    days_away: int


class TimelineResponse(BaseModel):
    timeline: list[TimelineItem]
