"""Pydantic schemas for policy configuration endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PolicyCreate(BaseModel):
    name: str
    config: dict


class PolicyUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None


class PolicyResponse(BaseModel):
    id: UUID
    name: str
    template_id: str | None
    config: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PolicyListResponse(BaseModel):
    policies: list[PolicyResponse]
