"""Pydantic schemas for report and alert endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReportGenerateRequest(BaseModel):
    period_days: int = 30
    include_examiner_simulation: bool = True


class ReportGenerateResponse(BaseModel):
    report_id: UUID
    status: str
    coverage_score: float | None
    maturity_level: str | None
    findings_count: int
    download_url: str


class ReportListItem(BaseModel):
    id: UUID
    report_type: str
    period_start: datetime
    period_end: datetime
    coverage_score: float | None
    maturity_level: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    reports: list[ReportListItem]


class AlertConfigRequest(BaseModel):
    on_block: bool = True
    on_flag: bool = False
    on_gap_detected: bool = True
    on_coverage_change: bool = False
    email_addresses: list[str] = []
    webhook_urls: list[str] = []


class AlertConfigResponse(BaseModel):
    id: UUID
    enabled: bool
    on_block: bool
    on_flag: bool
    on_gap_detected: bool
    on_coverage_change: bool
    email_addresses: list[str]
    webhook_urls: list[str]

    model_config = {"from_attributes": True}


class AlertHistoryItem(BaseModel):
    id: UUID
    trigger_type: str
    trigger_details: dict
    channels_sent: list
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertHistoryResponse(BaseModel):
    alerts: list[AlertHistoryItem]
    total: int
