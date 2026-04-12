"""Tests for content filter policy check."""

import pytest

from audithive.policy.checks.content import check_content


def _msgs(content: str) -> list[dict]:
    return [{"role": "user", "content": content}]


class TestContentFilter:

    def test_prohibited_topic_found(self) -> None:
        config = {"enabled": True, "prohibited_topics": ["competitor pricing"], "action": "block"}
        result = check_content(_msgs("Tell me about competitor pricing"), config)
        assert not result["passed"]
        assert result["action"] == "block"
        assert "competitor pricing" in result["details"]

    def test_no_prohibited_topics_passes(self) -> None:
        config = {"enabled": True, "prohibited_topics": ["competitor pricing"], "action": "block"}
        result = check_content(_msgs("What is our refund policy?"), config)
        assert result["passed"]

    def test_case_insensitive(self) -> None:
        config = {"enabled": True, "prohibited_topics": ["internal salary"], "action": "flag"}
        result = check_content(_msgs("What about INTERNAL SALARY data?"), config)
        assert not result["passed"]

    def test_multiple_topics_detected(self) -> None:
        config = {"enabled": True, "prohibited_topics": ["competitor pricing", "internal salary"], "action": "flag"}
        result = check_content(_msgs("Compare competitor pricing and internal salary"), config)
        assert not result["passed"]
        assert "competitor pricing" in result["details"]
        assert "internal salary" in result["details"]

    def test_disabled_passes(self) -> None:
        config = {"enabled": False, "prohibited_topics": ["competitor pricing"], "action": "block"}
        result = check_content(_msgs("Tell me about competitor pricing"), config)
        assert result["passed"]

    def test_empty_prohibited_list_passes(self) -> None:
        config = {"enabled": True, "prohibited_topics": [], "action": "block"}
        result = check_content(_msgs("Anything goes"), config)
        assert result["passed"]
