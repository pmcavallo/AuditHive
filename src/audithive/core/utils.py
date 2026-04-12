"""Shared utilities."""

from __future__ import annotations

from copy import deepcopy


def deep_merge(base: dict, overrides: dict) -> dict:
    """Recursively merge *overrides* into *base*.

    - Override values replace base values at leaf level.
    - Dicts are merged recursively.
    - Lists from overrides replace base lists entirely (not appended).
    - Keys in overrides not in base are added.
    - Keys in base not in overrides are preserved.
    - None values in overrides replace base values.

    Returns a new dict; neither input is mutated.
    """
    result = deepcopy(base)
    for key, override_val in overrides.items():
        base_val = result.get(key)
        if isinstance(base_val, dict) and isinstance(override_val, dict):
            result[key] = deep_merge(base_val, override_val)
        else:
            result[key] = deepcopy(override_val)
    return result
