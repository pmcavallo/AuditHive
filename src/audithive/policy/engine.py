"""Policy engine: runs a chain of policy checks against request messages."""

from __future__ import annotations

from dataclasses import dataclass, field

from audithive.policy.checks.content import check_content
from audithive.policy.checks.injection import check_injection
from audithive.policy.checks.pii import check_pii
from audithive.policy.checks.scope import check_scope

DEFAULT_POLICY_CONFIG: dict = {
    "pii_detection": {
        "enabled": True,
        "types": ["ssn", "credit_card"],
        "action": "flag",
    },
    "content_filter": {
        "enabled": False,
    },
    "injection_detection": {
        "enabled": True,
        "action": "flag",
    },
    "scope_enforcement": {
        "enabled": False,
    },
}


@dataclass
class PolicyCheckResult:
    check_name: str
    passed: bool
    action: str  # "allow", "flag", "block", "redact"
    details: str | None
    confidence: float


@dataclass
class PolicyEngineResult:
    allowed: bool
    action: str  # "allow", "flag", "block"
    checks: list[PolicyCheckResult] = field(default_factory=list)
    violations: list[PolicyCheckResult] = field(default_factory=list)


# Map of check name → check function
CHECK_REGISTRY: dict[str, callable] = {
    "pii_detection": check_pii,
    "content_filter": check_content,
    "injection_detection": check_injection,
    "scope_enforcement": check_scope,
}


def _is_template_format(config: dict) -> bool:
    """Detect whether config uses the template format (pre_call/post_call sections)."""
    return "pre_call" in config


def _normalize_pii_config(pii_cfg: dict) -> dict:
    """Normalize template-format PII config to the flat format the check function expects.

    Template format:
        {"enabled": true, "types": {"ssn": {"enabled": true, "action": "block"}, ...}}
    Flat format:
        {"enabled": true, "types": ["ssn", ...], "action": "block"}
    """
    if not pii_cfg.get("enabled", False):
        return {"enabled": False}

    types_field = pii_cfg.get("types", {})

    # Already flat format (list of strings)
    if isinstance(types_field, list):
        return pii_cfg

    # Template format: dict of type → {enabled, action}
    enabled_types: list[str] = []
    actions: list[str] = []
    for pii_type, type_cfg in types_field.items():
        if isinstance(type_cfg, dict) and type_cfg.get("enabled", True):
            enabled_types.append(pii_type)
            actions.append(type_cfg.get("action", "flag"))

    if not enabled_types:
        return {"enabled": False}

    # Use the most restrictive action: block > flag > allow
    if "block" in actions:
        overall_action = "block"
    elif "flag" in actions:
        overall_action = "flag"
    else:
        overall_action = "allow"

    return {
        "enabled": True,
        "types": enabled_types,
        "action": overall_action,
    }


def _normalize_template_config(config: dict) -> dict:
    """Convert template-format config to the flat format the check functions expect."""
    pre_call = config.get("pre_call", {})

    flat: dict = {}

    # PII detection — needs special normalization for per-type actions
    if "pii_detection" in pre_call:
        flat["pii_detection"] = _normalize_pii_config(pre_call["pii_detection"])
    else:
        flat["pii_detection"] = {"enabled": False}

    # Injection detection — already compatible
    if "injection_detection" in pre_call:
        flat["injection_detection"] = pre_call["injection_detection"]
    else:
        flat["injection_detection"] = {"enabled": False}

    # Content filter — already compatible
    if "content_filter" in pre_call:
        flat["content_filter"] = pre_call["content_filter"]
    else:
        flat["content_filter"] = {"enabled": False}

    # Scope enforcement — already compatible
    if "scope_enforcement" in pre_call:
        flat["scope_enforcement"] = pre_call["scope_enforcement"]
    else:
        flat["scope_enforcement"] = {"enabled": False}

    return flat


def run_policy_checks(
    messages: list[dict],
    policy_config: dict | None = None,
) -> PolicyEngineResult:
    """Run all enabled policy checks against the messages.

    Supports both flat format (Phase 2) and template format (Phase 3).
    Priority: block > flag > allow.
    """
    if policy_config is None:
        policy_config = DEFAULT_POLICY_CONFIG

    # Normalize template format to flat format for check functions
    if _is_template_format(policy_config):
        effective_config = _normalize_template_config(policy_config)
    else:
        effective_config = policy_config

    checks: list[PolicyCheckResult] = []
    violations: list[PolicyCheckResult] = []

    for check_name, check_fn in CHECK_REGISTRY.items():
        check_cfg = effective_config.get(check_name)
        result_dict = check_fn(messages, check_cfg)
        result = PolicyCheckResult(**result_dict)
        checks.append(result)
        if not result.passed:
            violations.append(result)

    # Determine overall action: block > flag > allow
    if any(v.action == "block" for v in violations):
        return PolicyEngineResult(
            allowed=False,
            action="block",
            checks=checks,
            violations=violations,
        )
    if any(v.action == "flag" for v in violations):
        return PolicyEngineResult(
            allowed=True,
            action="flag",
            checks=checks,
            violations=violations,
        )
    return PolicyEngineResult(
        allowed=True,
        action="allow",
        checks=checks,
        violations=violations,
    )
