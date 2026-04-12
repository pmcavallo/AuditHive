"""Add alert_configs, alert_history, examiner_reports tables.

Revision ID: 003
Revises: 002
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default="Default Alerts"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("on_block", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("on_flag", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("on_coverage_change", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("on_gap_detected", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("email_addresses", JSONB, nullable=False, server_default="[]"),
        sa.Column("webhook_urls", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_alert_configs_customer_id", "alert_configs", ["customer_id"])

    op.create_table(
        "alert_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("alert_config_id", UUID(as_uuid=True), sa.ForeignKey("alert_configs.id"), nullable=True),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("trigger_details", JSONB, nullable=False, server_default="{}"),
        sa.Column("channels_sent", JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_alert_history_customer_id", "alert_history", ["customer_id"])
    op.create_index("idx_alert_history_created_at", "alert_history", ["created_at"])

    op.create_table(
        "examiner_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("coverage_score", sa.Float, nullable=True),
        sa.Column("maturity_level", sa.String(20), nullable=True),
        sa.Column("regulations_count", sa.Integer, nullable=True),
        sa.Column("gaps_count", sa.Integer, nullable=True),
        sa.Column("examiner_narrative", sa.Text, nullable=True),
        sa.Column("examiner_questions", JSONB, server_default="[]"),
        sa.Column("examiner_findings", JSONB, server_default="[]"),
        sa.Column("recommendations", JSONB, server_default="[]"),
        sa.Column("report_html", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="generated"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_examiner_reports_customer_id", "examiner_reports", ["customer_id"])


def downgrade() -> None:
    op.drop_table("examiner_reports")
    op.drop_table("alert_history")
    op.drop_table("alert_configs")
