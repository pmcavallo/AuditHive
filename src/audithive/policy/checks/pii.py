"""PII detection policy check."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone": re.compile(r"\b\d{3}[\s.\-]?\d{3}[\s.\-]?\d{4}\b"),
}


@dataclass
class PIIMatch:
    pii_type: str
    matched_text: str


def detect_pii(
    text: str,
    enabled_types: list[str] | None = None,
) -> list[PIIMatch]:
    """Scan text for PII patterns. Returns list of matches."""
    if enabled_types is None:
        enabled_types = list(PII_PATTERNS.keys())

    matches: list[PIIMatch] = []
    for pii_type in enabled_types:
        pattern = PII_PATTERNS.get(pii_type)
        if not pattern:
            continue
        for m in pattern.finditer(text):
            matches.append(PIIMatch(pii_type=pii_type, matched_text=m.group()))
    return matches


def check_pii(
    messages: list[dict],
    config: dict | None = None,
) -> dict:
    """Run PII detection on all messages.

    Config shape:
        {"enabled": true, "types": ["ssn", "credit_card", ...], "action": "flag"}

    Returns a PolicyCheckResult-compatible dict.
    """
    if config is None:
        config = {"enabled": True, "types": ["ssn", "credit_card"], "action": "flag"}

    if not config.get("enabled", True):
        return {
            "check_name": "pii_detection",
            "passed": True,
            "action": "allow",
            "details": None,
            "confidence": 1.0,
        }

    enabled_types = config.get("types", ["ssn", "credit_card"])
    action = config.get("action", "flag")

    all_matches: list[PIIMatch] = []
    for msg in messages:
        content = msg.get("content", "")
        if content:
            all_matches.extend(detect_pii(content, enabled_types))

    if all_matches:
        types_found = sorted(set(m.pii_type for m in all_matches))
        return {
            "check_name": "pii_detection",
            "passed": False,
            "action": action,
            "details": f"PII detected: {', '.join(types_found)}",
            "confidence": 0.95,
        }

    return {
        "check_name": "pii_detection",
        "passed": True,
        "action": "allow",
        "details": None,
        "confidence": 1.0,
    }
