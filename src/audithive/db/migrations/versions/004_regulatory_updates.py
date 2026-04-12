"""Add regulatory_updates and customer_impact_assessments tables.

Revision ID: 004
Revises: 003
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "regulatory_updates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("regulation_short", sa.String(50), nullable=True),
        sa.Column("regulation_name", sa.String(255), nullable=True),
        sa.Column("update_type", sa.String(50), nullable=False),
        sa.Column("jurisdiction", sa.String(100), nullable=False),
        sa.Column("industries", JSONB, nullable=False, server_default='["any"]'),
        sa.Column("use_cases", JSONB, nullable=False, server_default='["any"]'),
        sa.Column("audiences", JSONB, nullable=False, server_default='["any"]'),
        sa.Column("required_actions", JSONB, nullable=False, server_default="[]"),
        sa.Column("affected_controls", JSONB, nullable=False, server_default="[]"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("effective_date", sa.Date, nullable=True),
        sa.Column("enforcement_date", sa.Date, nullable=True),
        sa.Column("deadline", sa.Date, nullable=True),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_reg_updates_jurisdiction", "regulatory_updates", ["jurisdiction"])
    op.create_index("idx_reg_updates_enforcement_date", "regulatory_updates", ["enforcement_date"])
    op.create_index("idx_reg_updates_is_active", "regulatory_updates", ["is_active"])

    op.create_table(
        "customer_impact_assessments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("regulatory_update_id", UUID(as_uuid=True), sa.ForeignKey("regulatory_updates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("impact_level", sa.String(20), nullable=False),
        sa.Column("is_affected", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("reasons", JSONB, nullable=False, server_default="[]"),
        sa.Column("controls_in_place", JSONB, nullable=False, server_default="[]"),
        sa.Column("controls_missing", JSONB, nullable=False, server_default="[]"),
        sa.Column("required_actions", JSONB, nullable=False, server_default="[]"),
        sa.Column("estimated_effort", sa.String(50), nullable=True),
        sa.Column("notified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("customer_id", "regulatory_update_id", name="uq_impact_customer_update"),
    )
    op.create_index("idx_impact_customer_id", "customer_impact_assessments", ["customer_id"])
    op.create_index("idx_impact_update_id", "customer_impact_assessments", ["regulatory_update_id"])


def downgrade() -> None:
    op.drop_table("customer_impact_assessments")
    op.drop_table("regulatory_updates")
