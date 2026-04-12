"""Shared FastAPI dependencies."""

# Re-export commonly used dependencies for convenience.
from audithive.api.middleware.auth import AuthenticatedCustomer, get_current_customer
from audithive.db.database import get_db

__all__ = ["get_db", "get_current_customer", "AuthenticatedCustomer"]
