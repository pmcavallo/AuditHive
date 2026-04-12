"""Add Row-Level Security policies to customer-scoped tables and ai_features_enabled column.

Revision ID: 005
Revises: 004
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RLS_TABLES = [
    "audit_logs",
    "policy_configs",
    "customer_profiles",
    "governance_assessments",
    "alert_configs",
    "alert_history",
    "examiner_reports",
    "customer_impact_assessments",
]


def upgrade() -> None:
    # Add ai_features_enabled column
    op.add_column("customer_profiles", sa.Column(
        "ai_features_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")
    ))

    # RLS is PostgreSQL-only; skip for SQLite
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_{table} ON {table} "
            f"USING (customer_id = current_setting('app.current_customer_id')::uuid)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in RLS_TABLES:
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_column("customer_profiles", "ai_features_enabled")
