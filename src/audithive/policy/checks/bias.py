"""Bias detection policy check.

Detects bias indicators in LLM prompts and responses:
- Protected class references in evaluative/decision contexts
- Demographic proxy variables in automated decision prompts
- Stereotypical association patterns
- Ungrounded group comparisons

Regulatory grounding:
- NIST AI RMF Manage 4.1: Track and respond to AI risks related to
  bias, fairness, and discrimination.
- EU AI Act Article 10: Training data governance including bias
  examination and mitigation for high-risk AI systems.
- FHFA AB 2022-02: Fair lending and bias concerns in AI/ML models
  used by regulated entities.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Protected class terms (federal protected classes + common proxies)
PROTECTED_CLASSES: set[str] = {
    "race", "racial", "ethnicity", "ethnic",
    "gender", "sex", "male", "female",
    "religion", "religious", "muslim", "christian", "jewish", "hindu",
    "national origin", "nationality", "immigrant", "foreign-born",
    "age", "elderly", "older workers",
    "disability", "disabled", "handicapped",
    "sexual orientation", "gay", "lesbian", "lgbtq",
    "pregnancy", "pregnant", "maternity",
    "marital status", "married", "single", "divorced",
    "veteran", "military status",
}

# Demographic proxy variables (facially neutral but correlate with
# protected classes in lending/insurance/employment decisions)
PROXY_VARIABLES: set[str] = {
    "zip code", "zipcode", "postal code",
    "neighborhood", "census tract",
    "school district", "university name", "college name",
    "language spoken", "primary language", "accent",
    "name-based", "surname",
    "social media activity", "online behavior",
    "commute distance", "transportation mode",
}

# Decision-making context indicators
DECISION_CONTEXTS: set[str] = {
    "approve", "deny", "reject", "decline",
    "score", "rank", "evaluate", "assess",
    "eligible", "ineligible", "eligibility", "qualify", "disqualify",
    "hire", "terminate", "promote", "demote",
    "underwrite", "price", "rate", "tier",
    "recommend", "flag", "escalate", "determine",
    "credit decision", "loan decision", "lending decision",
    "risk score", "risk rating", "risk tier",
    "insurance decision", "claims decision",
}

# Stereotypical association patterns
STEREOTYPE_PATTERNS: list[re.Pattern[str]] = [
    # "X are [more/less/not] ..."
    re.compile(
        r"\b(men|women|males|females|blacks|whites|asians|hispanics|latinos"
        r"|immigrants|elderly|disabled|muslims|christians|jews)\b"
        r"\s+(are|tend to be|are usually|are typically|are generally|are more"
        r"|are less|are not|aren't|cannot|can't)\s+",
        re.IGNORECASE,
    ),
    # "because of their [protected class]"
    re.compile(
        r"\bbecause\s+of\s+(their|his|her)\s+"
        r"(race|gender|sex|age|religion|ethnicity|disability|national origin"
        r"|sexual orientation|marital status|pregnancy)\b",
        re.IGNORECASE,
    ),
    # "typical [group] behavior"
    re.compile(
        r"\btypical\s+(male|female|minority|immigrant|elderly)\s+"
        r"(behavior|behaviour|attitude|tendency|characteristic)",
        re.IGNORECASE,
    ),
]


@dataclass
class BiasMatch:
    """A single bias indicator detected in text."""

    bias_type: str  # protected_class, proxy_variable, stereotype, disparate_context
    matched_text: str
    context: str  # surrounding text for review


def _find_term_in_text(text: str, terms: set[str]) -> list[tuple[str, int, int]]:
    """Find occurrences of multi-word terms in text. Returns (term, start, end)."""
    found: list[tuple[str, int, int]] = []
    text_lower = text.lower()
    for term in terms:
        start = 0
        while True:
            idx = text_lower.find(term, start)
            if idx == -1:
                break
            # Check word boundaries
            before_ok = idx == 0 or not text_lower[idx - 1].isalnum()
            after_idx = idx + len(term)
            after_ok = after_idx >= len(text_lower) or not text_lower[after_idx].isalnum()
            if before_ok and after_ok:
                found.append((term, idx, after_idx))
            start = idx + 1
    return found


def _get_context(text: str, start: int, end: int, window: int = 60) -> str:
    """Extract surrounding context for a match."""
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    snippet = text[ctx_start:ctx_end].strip()
    if ctx_start > 0:
        snippet = "..." + snippet
    if ctx_end < len(text):
        snippet = snippet + "..."
    return snippet


def detect_bias_indicators(
    text: str,
    check_protected_classes: bool = True,
    check_proxies: bool = True,
    check_stereotypes: bool = True,
) -> list[BiasMatch]:
    """Scan text for bias indicators. Returns list of matches.

    This is a pattern-based detector, not a fairness auditor.
    It flags content that warrants human review, not content that
    is definitively biased.
    """
    matches: list[BiasMatch] = []

    # 1. Protected class terms in decision-making contexts
    if check_protected_classes:
        protected_hits = _find_term_in_text(text, PROTECTED_CLASSES)
        decision_hits = _find_term_in_text(text, DECISION_CONTEXTS)

        if protected_hits and decision_hits:
            for term, start, end in protected_hits:
                matches.append(BiasMatch(
                    bias_type="protected_class_in_decision",
                    matched_text=term,
                    context=_get_context(text, start, end),
                ))

    # 2. Demographic proxy variables in decision contexts
    if check_proxies:
        proxy_hits = _find_term_in_text(text, PROXY_VARIABLES)
        if proxy_hits:
            decision_hits = _find_term_in_text(text, DECISION_CONTEXTS)
            if decision_hits:
                for term, start, end in proxy_hits:
                    matches.append(BiasMatch(
                        bias_type="proxy_variable",
                        matched_text=term,
                        context=_get_context(text, start, end),
                    ))

    # 3. Stereotypical association patterns
    if check_stereotypes:
        for pattern in STEREOTYPE_PATTERNS:
            for m in pattern.finditer(text):
                matches.append(BiasMatch(
                    bias_type="stereotype",
                    matched_text=m.group().strip(),
                    context=_get_context(text, m.start(), m.end()),
                ))

    return matches


def check_bias(
    messages: list[dict],
    config: dict | None = None,
) -> dict:
    """Run bias detection on all messages.

    Config shape:
        {
            "enabled": true,
            "check_protected_classes": true,
            "check_proxies": true,
            "check_stereotypes": true,
            "action": "flag"
        }

    Returns a PolicyCheckResult-compatible dict.
    """
    if config is None:
        config = {
            "enabled": True,
            "check_protected_classes": True,
            "check_proxies": True,
            "check_stereotypes": True,
            "action": "flag",
        }

    if not config.get("enabled", True):
        return {
            "check_name": "bias_detection",
            "passed": True,
            "action": "allow",
            "details": None,
            "confidence": 1.0,
        }

    action = config.get("action", "flag")

    all_matches: list[BiasMatch] = []
    for msg in messages:
        content = msg.get("content", "")
        if content:
            all_matches.extend(detect_bias_indicators(
                content,
                check_protected_classes=config.get("check_protected_classes", True),
                check_proxies=config.get("check_proxies", True),
                check_stereotypes=config.get("check_stereotypes", True),
            ))

    if all_matches:
        bias_types_found = sorted(set(m.bias_type for m in all_matches))
        return {
            "check_name": "bias_detection",
            "passed": False,
            "action": action,
            "details": f"Bias indicators detected: {', '.join(bias_types_found)}",
            "matches": [
                {
                    "bias_type": m.bias_type,
                    "matched_text": m.matched_text,
                    "context": m.context,
                }
                for m in all_matches
            ],
            "confidence": 0.80,
        }

    return {
        "check_name": "bias_detection",
        "passed": True,
        "action": "allow",
        "details": None,
        "confidence": 1.0,
    }
