"""Tests for regulatory mapping seed data and querying."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from audithive.db.models import RegulatoryMapping
from scripts.seed_regulatory_mappings import seed, MAPPINGS


@pytest.mark.asyncio
async def test_seed_loads_all_mappings(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        count = await seed(session)
        await session.commit()
    assert count == len(MAPPINGS)


@pytest.mark.asyncio
async def test_query_by_jurisdiction(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed(session)
        await session.commit()
        result = await session.execute(
            select(RegulatoryMapping).where(RegulatoryMapping.jurisdiction == "california")
        )
        ca_regs = result.scalars().all()
    assert len(ca_regs) >= 2  # CCPA, SB 243, AI Transparency Act


@pytest.mark.asyncio
async def test_query_by_industry(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed(session)
        await session.commit()
        result = await session.execute(
            select(RegulatoryMapping).where(RegulatoryMapping.industry == "financial_services")
        )
        fin_regs = result.scalars().all()
    assert len(fin_regs) >= 2  # SR 11-7, FINRA


@pytest.mark.asyncio
async def test_wildcard_matching(engine) -> None:
    """industry='any' should exist for broad regulations."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed(session)
        await session.commit()
        result = await session.execute(
            select(RegulatoryMapping).where(RegulatoryMapping.industry == "any")
        )
        any_regs = result.scalars().all()
    assert len(any_regs) >= 10


@pytest.mark.asyncio
async def test_composite_query(engine) -> None:
    """Query by industry + jurisdiction + use_case returns union of matches."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed(session)
        await session.commit()
        result = await session.execute(
            select(RegulatoryMapping).where(
                RegulatoryMapping.jurisdiction.in_(["california", "us_federal"]),
                RegulatoryMapping.use_case.in_(["customer_chatbot", "any"]),
            )
        )
        regs = result.scalars().all()
    assert len(regs) >= 3
