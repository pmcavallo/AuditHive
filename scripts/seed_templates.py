"""Seed policy templates from JSON definition files."""

import asyncio
import sys

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from audithive.core.config import settings
from audithive.policy.templates.loader import load_templates_from_definitions


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        templates = await load_templates_from_definitions(session)
        await session.commit()

    print(f"Loaded {len(templates)} templates:")
    for t in templates:
        print(f"  - {t.id}: {t.name} (v{t.version}, {t.use_case})")

    await engine.dispose()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
