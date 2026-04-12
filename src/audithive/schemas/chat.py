"""Pydantic schemas for chat completion endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4"
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    stop: list[str] | str | None = None
    n: int | None = None

    def to_openai_dict(self) -> dict:
        """Convert to dict for OpenAI API, excluding None values."""
        d: dict = {"model": self.model, "messages": [m.model_dump() for m in self.messages]}
        for key in ("temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty", "stop", "n"):
            val = getattr(self, key)
            if val is not None:
                d[key] = val
        return d


class PolicyViolationResponse(BaseModel):
    error: str = "policy_violation"
    message: str
    action: str
    violations: list[dict]
    audit_log_id: str
