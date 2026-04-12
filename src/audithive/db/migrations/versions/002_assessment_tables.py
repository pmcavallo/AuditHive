"""Add customer_profiles, regulatory_mappings, governance_assessments tables.

Revision ID: 002
Revises: 001
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("ai_use_cases", JSONB, nullable=False, server_default="[]"),
        sa.Column("audience_types", JSONB, nullable=False, server_default="[]"),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("jurisdictions", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "regulatory_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("regulation_name", sa.String(255), nullable=False),
        sa.Column("regulation_short", sa.String(50), nullable=False),
        sa.Column("jurisdiction", sa.String(100), nullable=False),
        sa.Column("industry", sa.String(100), nullable=False, server_default="any"),
        sa.Column("use_case", sa.String(100), nullable=False, server_default="any"),
        sa.Column("audience", sa.String(100), nullable=False, server_default="any"),
        sa.Column("required_controls", JSONB, nullable=False, server_default="[]"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("effective_date", sa.Date, nullable=True),
        sa.Column("enforcement_date", sa.Date, nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_reg_mappings_jurisdiction", "regulatory_mappings", ["jurisdiction"])
    op.create_index("idx_reg_mappings_industry", "regulatory_mappings", ["industry"])
    op.create_index("idx_reg_mappings_use_case", "regulatory_mappings", ["use_case"])

    op.create_table(
        "governance_assessments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("applicable_regulations", JSONB, nullable=False, server_default="[]"),
        sa.Column("required_controls", JSONB, nullable=False, server_default="[]"),
        sa.Column("current_controls", JSONB, nullable=False, server_default="[]"),
        sa.Column("missing_controls", JSONB, nullable=False, server_default="[]"),
        sa.Column("coverage_score", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("maturity_level", sa.String(20), nullable=False, server_default="ungoverned"),
        sa.Column("four_questions", JSONB, nullable=False, server_default="{}"),
        sa.Column("examiner_questions", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_assessments_customer_id", "governance_assessments", ["customer_id"])


def downgrade() -> None:
    op.drop_table("governance_assessments")
    op.drop_table("regulatory_mappings")
    op.drop_table("customer_profiles")
