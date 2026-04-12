"""Tests for PII detection policy check."""

import pytest

from audithive.policy.checks.pii import check_pii


def _msgs(content: str) -> list[dict]:
    return [{"role": "user", "content": content}]


class TestPIIDetection:

    def test_ssn_detected(self) -> None:
        result = check_pii(_msgs("My SSN is 123-45-6789"), {"enabled": True, "types": ["ssn"], "action": "block"})
        assert not result["passed"]
        assert result["action"] == "block"
        assert "ssn" in result["details"]

    def test_credit_card_detected(self) -> None:
        result = check_pii(_msgs("Card: 4111-1111-1111-1111"), {"enabled": True, "types": ["credit_card"], "action": "flag"})
        assert not result["passed"]
        assert "credit_card" in result["details"]

    def test_email_detected(self) -> None:
        result = check_pii(_msgs("Email me at user@example.com"), {"enabled": True, "types": ["email"], "action": "flag"})
        assert not result["passed"]
        assert "email" in result["details"]

    def test_phone_detected(self) -> None:
        result = check_pii(_msgs("Call me at 555-123-4567"), {"enabled": True, "types": ["phone"], "action": "flag"})
        assert not result["passed"]
        assert "phone" in result["details"]

    def test_clean_message_passes(self) -> None:
        result = check_pii(_msgs("What is your refund policy?"), {"enabled": True, "types": ["ssn", "credit_card", "email", "phone"], "action": "block"})
        assert result["passed"]
        assert result["action"] == "allow"

    def test_pii_in_system_message_detected(self) -> None:
        msgs = [{"role": "system", "content": "SSN: 111-22-3333"}]
        result = check_pii(msgs, {"enabled": True, "types": ["ssn"], "action": "block"})
        assert not result["passed"]

    def test_mixed_pii_types_all_detected(self) -> None:
        result = check_pii(
            _msgs("SSN 123-45-6789 and card 4111 1111 1111 1111"),
            {"enabled": True, "types": ["ssn", "credit_card"], "action": "flag"},
        )
        assert not result["passed"]
        assert "ssn" in result["details"]
        assert "credit_card" in result["details"]

    def test_disabled_type_not_flagged(self) -> None:
        result = check_pii(_msgs("My SSN is 123-45-6789"), {"enabled": True, "types": ["credit_card"], "action": "block"})
        assert result["passed"]

    def test_disabled_check_passes(self) -> None:
        result = check_pii(_msgs("My SSN is 123-45-6789"), {"enabled": False})
        assert result["passed"]
