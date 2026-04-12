"""Webhook alert channel."""

from __future__ import annotations

import logging

import httpx

from audithive.core.config import settings

logger = logging.getLogger(__name__)


async def send_webhook_alert(
    webhook_url: str,
    payload: dict,
) -> bool:
    """POST alert payload to a webhook URL. Returns True on success."""
    try:
        async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT_SECONDS) as client:
            resp = await client.post(webhook_url, json=payload)
        return resp.status_code < 400
    except Exception as e:
        logger.error("Webhook alert failed for %s: %s", webhook_url, e)
        return False
