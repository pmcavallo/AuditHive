"""Alert dispatcher — checks config and sends to enabled channels."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.alerts.channels.email import send_email_alert
from audithive.alerts.channels.webhook import send_webhook_alert
from audithive.db.models import AlertConfig, AlertHistory

logger = logging.getLogger(__name__)

TRIGGER_TO_CONFIG_FIELD = {
    "policy_block": "on_block",
    "policy_flag": "on_flag",
    "gap_detected": "on_gap_detected",
    "coverage_change": "on_coverage_change",
}


async def dispatch_alert(
    db: AsyncSession,
    customer_id: UUID,
    trigger_type: str,
    trigger_details: dict,
) -> None:
    """Check customer's alert config and send to configured channels."""
    result = await db.execute(
        select(AlertConfig).where(
            AlertConfig.customer_id == customer_id,
            AlertConfig.enabled.is_(True),
        )
    )
    configs = result.scalars().all()

    for config in configs:
        # Check if this trigger type is enabled
        config_field = TRIGGER_TO_CONFIG_FIELD.get(trigger_type)
        if config_field and not getattr(config, config_field, False):
            continue

        channels_sent: list[str] = []
        errors: list[str] = []

        # Email
        if config.email_addresses:
            subject = f"AuditHive Alert: {trigger_type.replace('_', ' ').title()}"
            body = (
                f"<h2>AuditHive Alert</h2>"
                f"<p><strong>Type:</strong> {trigger_type}</p>"
                f"<p><strong>Details:</strong> {trigger_details}</p>"
                f"<p><a href='https://app.audithive.io'>View in Dashboard</a></p>"
            )
            ok = await send_email_alert(config.email_addresses, subject, body)
            if ok:
                channels_sent.append("email")
            else:
                errors.append("email_failed")

        # Webhooks
        for url in config.webhook_urls:
            payload = {
                "event": trigger_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "customer_id": str(customer_id),
                "details": trigger_details,
            }
            ok = await send_webhook_alert(url, payload)
            if ok:
                channels_sent.append(f"webhook:{url[:50]}")
            else:
                errors.append(f"webhook_failed:{url[:50]}")

        # Log to history
        history = AlertHistory(
            customer_id=customer_id,
            alert_config_id=config.id,
            trigger_type=trigger_type,
            trigger_details=trigger_details,
            channels_sent=channels_sent,
            status="sent" if channels_sent else "failed",
            error_message="; ".join(errors) if errors else None,
        )
        db.add(history)

    await db.flush()
