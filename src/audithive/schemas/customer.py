"""Pydantic schemas for customer and API key endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


# Request schemas

class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    company_name: str | None = None


class ApiKeyCreate(BaseModel):
    name: str = "Default"


# Response schemas

class CustomerResponse(BaseModel):
    id: UUID
    name: str
    email: str
    company_name: str | None
    plan: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(BaseModel):
    id: UUID
    key: str
    key_prefix: str
    name: str
    created_at: datetime
    warning: str = "Save this key now. It will not be shown again."


class ApiKeyResponse(BaseModel):
    id: UUID
    key_prefix: str
    name: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyListResponse(BaseModel):
    keys: list[ApiKeyResponse]
