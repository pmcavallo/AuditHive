"""Prompt injection detection policy check."""

from __future__ import annotations

import re

INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(your\s+)?instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\b", re.IGNORECASE),
    re.compile(r"new\s+instructions\s*:", re.IGNORECASE),
    re.compile(r"system\s+prompt\s*:", re.IGNORECASE),
    re.compile(r"as\s+an\s+ai\s+with\s+no\s+restrictions", re.IGNORECASE),
    re.compile(r"ignore\s+all\s+previous", re.IGNORECASE),
]


def check_injection(
    messages: list[dict],
    config: dict | None = None,
) -> dict:
    """Detect prompt injection attempts in user messages.

    Config shape:
        {"enabled": true, "action": "block"}

    Returns a PolicyCheckResult-compatible dict.
    """
    if config is None:
        config = {"enabled": True, "action": "block"}

    if not config.get("enabled", True):
        return {
            "check_name": "injection_detection",
            "passed": True,
            "action": "allow",
            "details": None,
            "confidence": 1.0,
        }

    action = config.get("action", "block")

    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = msg.get("content") or ""
        for pattern in INJECTION_PATTERNS:
            if pattern.search(content):
                return {
                    "check_name": "injection_detection",
                    "passed": False,
                    "action": action,
                    "details": f"Prompt injection pattern detected: {pattern.pattern}",
                    "confidence": 0.85,
                }

    return {
        "check_name": "injection_detection",
        "passed": True,
        "action": "allow",
        "details": None,
        "confidence": 1.0,
    }
