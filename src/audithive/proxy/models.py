"""Proxy response model — shared by llm_proxy and providers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProxyResponse:
    status_code: int
    body: dict
    latency_ms: int
    error: str | None = None
