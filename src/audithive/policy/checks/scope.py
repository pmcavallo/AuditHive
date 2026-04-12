"""Scope enforcement policy check."""

from __future__ import annotations


def check_scope(
    messages: list[dict],
    config: dict | None = None,
) -> dict:
    """Check if user messages stay within defined topic boundaries.

    Config shape:
        {
            "enabled": true,
            "allowed_topics": ["customer support", "product questions", "order status"],
            "scope_description": "...",
            "action": "flag"
        }

    MVP: keyword matching against allowed_topics.
    Returns a PolicyCheckResult-compatible dict.
    """
    if config is None:
        config = {"enabled": False}

    if not config.get("enabled", False):
        return {
            "check_name": "scope_enforcement",
            "passed": True,
            "action": "allow",
            "details": None,
            "confidence": 1.0,
        }

    allowed_topics = config.get("allowed_topics", [])
    action = config.get("action", "flag")

    if not allowed_topics:
        return {
            "check_name": "scope_enforcement",
            "passed": True,
            "action": "allow",
            "details": None,
            "confidence": 1.0,
        }

    # Check user messages only
    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = (msg.get("content") or "").lower()
        # If any allowed topic keyword is found, consider it in-scope
        topic_found = any(topic.lower() in content for topic in allowed_topics)
        if not topic_found:
            return {
                "check_name": "scope_enforcement",
                "passed": False,
                "action": action,
                "details": f"Message may be out of scope. Allowed topics: {', '.join(allowed_topics)}",
                "confidence": 0.6,
            }

    return {
        "check_name": "scope_enforcement",
        "passed": True,
        "action": "allow",
        "details": None,
        "confidence": 0.8,
    }
