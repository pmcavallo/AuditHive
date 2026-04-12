"""Test fixtures for AuditHive."""

import asyncio
from collections.abc import AsyncGenerator
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from audithive.core.security import generate_api_key
from audithive.db.database import get_db
from audithive.db.models import ApiKey, Base, Customer

# Use in-memory SQLite for tests (no PostgreSQL dependency).
TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def engine():
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with the test database."""
    from audithive.api.app import create_app

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_customer(client: AsyncClient) -> dict:
    """Create a test customer and return the response body."""
    resp = await client.post(
        "/v1/customers",
        json={
            "name": "Alex Testperson",
            "email": "alex@testcompany.com",
            "company_name": "Test Company Inc.",
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def test_api_key(client: AsyncClient, test_customer: dict) -> dict:
    """Create a test API key and return the response body (includes full key)."""
    resp = await client.post(
        f"/v1/customers/{test_customer['id']}/api-keys",
        json={"name": "Test Key"},
    )
    assert resp.status_code == 201
    return resp.json()
