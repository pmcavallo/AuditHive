"""Shared test helpers for seeding regulatory mappings."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from scripts.seed_regulatory_mappings import seed


async def seed_regulatory_mappings(engine) -> None:
    """Seed regulatory mappings into the test database."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed(session)
        await session.commit()
