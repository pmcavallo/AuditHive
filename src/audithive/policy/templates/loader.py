"""Template loader: reads JSON definitions and seeds the database."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.db.models import PolicyTemplate

DEFINITIONS_DIR = Path(__file__).parent / "definitions"


async def load_templates_from_definitions(db: AsyncSession) -> list[PolicyTemplate]:
    """Load all template JSON files from the definitions directory into the database.

    - Inserts new templates.
    - Updates existing templates if the JSON version is higher.
    - Skips templates whose version matches.

    Returns list of all templates in the database after loading.
    """
    json_files = sorted(DEFINITIONS_DIR.glob("*.json"))

    for json_path in json_files:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        template_id = data["id"]
        json_version = data.get("version", 1)

        result = await db.execute(
            select(PolicyTemplate).where(PolicyTemplate.id == template_id)
        )
        existing = result.scalar_one_or_none()

        # Build the config blob: policy config + metadata fields
        config_blob = dict(data.get("config", {}))
        config_blob["risk_level"] = data.get("risk_level", "medium")
        config_blob["regulatory_grounding"] = data.get("regulatory_grounding", [])

        if existing is None:
            template = PolicyTemplate(
                id=template_id,
                name=data["name"],
                description=data.get("description", ""),
                use_case=data["use_case"],
                config=config_blob,
                version=json_version,
            )
            db.add(template)
        elif json_version > existing.version:
            existing.name = data["name"]
            existing.description = data.get("description", "")
            existing.use_case = data["use_case"]
            existing.config = config_blob
            existing.version = json_version

    await db.flush()

    # Return all templates
    result = await db.execute(select(PolicyTemplate).order_by(PolicyTemplate.id))
    return list(result.scalars().all())
