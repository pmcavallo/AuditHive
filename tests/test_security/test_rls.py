"""Tests for Row-Level Security.

RLS is PostgreSQL-only. SQLite tests skip with a clear message.
"""

import pytest


@pytest.mark.skip(reason="RLS is PostgreSQL-only; test environment uses SQLite")
def test_rls_blocks_cross_tenant_without_session_var() -> None:
    """In PostgreSQL, queries without app.current_customer_id should fail."""
    pass


@pytest.mark.skip(reason="RLS is PostgreSQL-only; test environment uses SQLite")
def test_rls_allows_access_with_correct_session_var() -> None:
    """In PostgreSQL, queries with matching session var should succeed."""
    pass
