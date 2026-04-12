"""Content filter policy check."""

from __future__ import annotations


def check_content(
    messages: list[dict],
    config: dict | None = None,
) -> dict:
    """Check messages for prohibited topics (case-insensitive keyword match).

    Config shape:
        {
            "enabled": true,
            "prohibited_topics": ["competitor pricing", "internal salary"],
            "required_disclaimers": [],
            "action": "block"
        }

    Returns a PolicyCheckResult-compatible dict.
    """
    if config is None:
        config = {"enabled": False}

    if not config.get("enabled", False):
        return {
            "check_name": "content_filter",
            "passed": True,
            "action": "allow",
            "details": None,
            "confidence": 1.0,
        }

    prohibited = config.get("prohibited_topics", [])
    action = config.get("action", "flag")

    if not prohibited:
        return {
            "check_name": "content_filter",
            "passed": True,
            "action": "allow",
            "details": None,
            "confidence": 1.0,
        }

    found_topics: list[str] = []
    for msg in messages:
        content = (msg.get("content") or "").lower()
        for topic in prohibited:
            if topic.lower() in content:
                found_topics.append(topic)

    found_topics = sorted(set(found_topics))

    if found_topics:
        return {
            "check_name": "content_filter",
            "passed": False,
            "action": action,
            "details": f"Prohibited topics found: {', '.join(found_topics)}",
            "confidence": 0.9,
        }

    return {
        "check_name": "content_filter",
        "passed": True,
        "action": "allow",
        "details": None,
        "confidence": 1.0,
    }
