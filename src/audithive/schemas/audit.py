"""Pydantic schemas for audit log endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: UUID
    customer_id: UUID
    api_key_id: UUID | None
    request_model: str | None
    request_messages: list[dict] | None
    request_params: dict | None
    response_content: dict | None
    response_tokens_in: int | None
    response_tokens_out: int | None
    response_latency_ms: int | None
    policies_applied: list[dict] | None
    policies_violated: list[dict] | None
    action_taken: str | None
    evaluation_scores: dict | None
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    logs: list[AuditLogResponse]
    total: int
    limit: int
    offset: int


class DayStats(BaseModel):
    date: str
    total: int
    violations: int


class RecentViolation(BaseModel):
    id: UUID
    created_at: datetime
    status: str
    request_model: str | None
    message_preview: str
    policies_violated: list[dict]


class AuditLogStatsResponse(BaseModel):
    total_calls: int
    total_blocked: int
    total_flagged: int
    total_completed: int
    active_policies: int
    calls_by_day: list[DayStats]
    recent_violations: list[RecentViolation]
