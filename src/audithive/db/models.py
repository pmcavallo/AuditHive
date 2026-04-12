"""SQLAlchemy 2.0 models for all AuditHive tables."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Date,
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    api_keys: Mapped[list[ApiKey]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    policy_configs: Mapped[list[PolicyConfig]] = relationship(back_populates="customer", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Default")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped[Customer] = relationship(back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_keys_customer_id", "customer_id"),
        Index("idx_api_keys_key_prefix", "key_prefix"),
    )


class PolicyConfig(Base):
    __tablename__ = "policy_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped[Customer] = relationship(back_populates="policy_configs")

    __table_args__ = (
        UniqueConstraint("customer_id", "name", name="uq_policy_configs_customer_name"),
        Index("idx_policy_configs_customer_id", "customer_id"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id"), nullable=False
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("api_keys.id"), nullable=True
    )

    # Request
    request_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_messages: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    request_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Response
    response_content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Governance
    policies_applied: Mapped[dict] = mapped_column(JSON, default=list)
    policies_violated: Mapped[dict] = mapped_column(JSON, default=list)
    action_taken: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Evaluation (Phase 2)
    evaluation_scores: Mapped[dict] = mapped_column(JSON, default=dict)

    # Meta
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_audit_logs_customer_id", "customer_id"),
        Index("idx_audit_logs_created_at", "created_at"),
        Index("idx_audit_logs_status", "status"),
    )


class PolicyTemplate(Base):
    __tablename__ = "policy_templates"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    use_case: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    ai_use_cases: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    audience_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    jurisdictions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    ai_features_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RegulatoryMapping(Base):
    __tablename__ = "regulatory_mappings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    regulation_name: Mapped[str] = mapped_column(String(255), nullable=False)
    regulation_short: Mapped[str] = mapped_column(String(50), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False)
    industry: Mapped[str] = mapped_column(String(100), nullable=False, default="any")
    use_case: Mapped[str] = mapped_column(String(100), nullable=False, default="any")
    audience: Mapped[str] = mapped_column(String(100), nullable=False, default="any")
    required_controls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    enforcement_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_reg_mappings_jurisdiction", "jurisdiction"),
        Index("idx_reg_mappings_industry", "industry"),
        Index("idx_reg_mappings_use_case", "use_case"),
    )


class GovernanceAssessment(Base):
    __tablename__ = "governance_assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    applicable_regulations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    required_controls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    current_controls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    missing_controls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    coverage_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    maturity_level: Mapped[str] = mapped_column(String(20), nullable=False, default="ungoverned")
    four_questions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    examiner_questions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_assessments_customer_id", "customer_id"),
    )


class AlertConfig(Base):
    __tablename__ = "alert_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Default Alerts")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    on_block: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    on_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    on_coverage_change: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    on_gap_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_addresses: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    webhook_urls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_alert_configs_customer_id", "customer_id"),
    )


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id"), nullable=False
    )
    alert_config_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("alert_configs.id"), nullable=True
    )
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    channels_sent: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sent")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_alert_history_customer_id", "customer_id"),
        Index("idx_alert_history_created_at", "created_at"),
    )


class ExaminerReport(Base):
    __tablename__ = "examiner_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    coverage_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    maturity_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    regulations_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gaps_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    examiner_narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    examiner_questions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    examiner_findings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recommendations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    report_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="generated")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_examiner_reports_customer_id", "customer_id"),
    )


class RegulatoryUpdate(Base):
    __tablename__ = "regulatory_updates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    regulation_short: Mapped[str | None] = mapped_column(String(50), nullable=True)
    regulation_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    update_type: Mapped[str] = mapped_column(String(50), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False)
    industries: Mapped[list] = mapped_column(JSON, nullable=False, default=lambda: ["any"])
    use_cases: Mapped[list] = mapped_column(JSON, nullable=False, default=lambda: ["any"])
    audiences: Mapped[list] = mapped_column(JSON, nullable=False, default=lambda: ["any"])
    required_actions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    affected_controls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    effective_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    enforcement_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_reg_updates_jurisdiction", "jurisdiction"),
        Index("idx_reg_updates_enforcement_date", "enforcement_date"),
        Index("idx_reg_updates_is_active", "is_active"),
    )


class CustomerImpactAssessment(Base):
    __tablename__ = "customer_impact_assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    regulatory_update_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("regulatory_updates.id", ondelete="CASCADE"), nullable=False
    )
    impact_level: Mapped[str] = mapped_column(String(20), nullable=False)
    is_affected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    controls_in_place: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    controls_missing: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    required_actions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    estimated_effort: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("customer_id", "regulatory_update_id", name="uq_impact_customer_update"),
        Index("idx_impact_customer_id", "customer_id"),
        Index("idx_impact_update_id", "regulatory_update_id"),
    )
