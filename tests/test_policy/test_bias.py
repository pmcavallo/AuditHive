"""Tests for bias detection policy check.

Standard: 3+ positive, 3+ negative, 2+ edge cases.
"""

from __future__ import annotations

import pytest

from audithive.policy.checks.bias import (
    BiasMatch,
    check_bias,
    detect_bias_indicators,
)


# ---------------------------------------------------------------------------
# detect_bias_indicators — unit tests
# ---------------------------------------------------------------------------

class TestDetectBiasIndicators:
    """Tests for the core detection function."""

    # --- Positive cases: SHOULD detect bias indicators ---

    def test_protected_class_in_credit_decision(self):
        """Protected class term + decision context = flag."""
        text = "Use the applicant's race and income to score their credit application."
        matches = detect_bias_indicators(text)
        assert len(matches) >= 1
        assert any(m.bias_type == "protected_class_in_decision" for m in matches)

    def test_gender_in_hiring_decision(self):
        """Gender reference in employment decision context."""
        text = "Evaluate whether to hire the candidate. Consider that female applicants may need more flexible schedules."
        matches = detect_bias_indicators(text)
        assert len(matches) >= 1
        types = {m.bias_type for m in matches}
        assert "protected_class_in_decision" in types or "stereotype" in types

    def test_proxy_variable_in_lending(self):
        """Demographic proxy in lending decision = flag."""
        text = "Use the applicant's zip code and school district to determine loan eligibility."
        matches = detect_bias_indicators(text)
        assert len(matches) >= 1
        assert any(m.bias_type == "proxy_variable" for m in matches)

    def test_stereotype_pattern_group_generalization(self):
        """Stereotypical group generalization detected."""
        text = "Women are typically less assertive in negotiations."
        matches = detect_bias_indicators(text)
        assert len(matches) >= 1
        assert any(m.bias_type == "stereotype" for m in matches)

    def test_stereotype_pattern_because_of_protected_class(self):
        """'Because of their [protected class]' pattern."""
        text = "The model flagged the applicant because of their national origin."
        matches = detect_bias_indicators(text)
        assert len(matches) >= 1
        assert any(m.bias_type == "stereotype" for m in matches)

    def test_multiple_proxy_variables(self):
        """Multiple proxy variables in one prompt."""
        text = "Score the applicant using zip code, neighborhood, and commute distance to approve the loan."
        matches = detect_bias_indicators(text)
        proxy_matches = [m for m in matches if m.bias_type == "proxy_variable"]
        assert len(proxy_matches) >= 2

    # --- Negative cases: SHOULD NOT flag ---

    def test_clean_credit_decision(self):
        """Standard credit decision without bias indicators."""
        text = "Evaluate the applicant's debt-to-income ratio, payment history, and credit utilization to determine eligibility."
        matches = detect_bias_indicators(text)
        assert len(matches) == 0

    def test_protected_class_without_decision_context(self):
        """Protected class term in informational context (no decision)."""
        text = "Provide a summary of age discrimination laws in the United States."
        matches = detect_bias_indicators(text)
        # No decision context, so protected_class_in_decision should not fire
        pc_matches = [m for m in matches if m.bias_type == "protected_class_in_decision"]
        assert len(pc_matches) == 0

    def test_proxy_variable_without_decision_context(self):
        """Proxy variable in non-decision context."""
        text = "What is the average household income by zip code in Texas?"
        matches = detect_bias_indicators(text)
        proxy_matches = [m for m in matches if m.bias_type == "proxy_variable"]
        assert len(proxy_matches) == 0

    def test_clean_hr_prompt(self):
        """HR prompt without bias indicators."""
        text = "Draft a job description for a senior software engineer role emphasizing Python and cloud experience."
        matches = detect_bias_indicators(text)
        assert len(matches) == 0

    # --- Edge cases ---

    def test_empty_text(self):
        """Empty string produces no matches."""
        matches = detect_bias_indicators("")
        assert len(matches) == 0

    def test_case_insensitive_detection(self):
        """Detection works regardless of casing."""
        text = "WOMEN ARE TYPICALLY more risk-averse in investment decisions."
        matches = detect_bias_indicators(text)
        assert len(matches) >= 1

    def test_disabled_check_types(self):
        """Disabling specific check types suppresses those matches."""
        text = "Use zip code to approve the loan for the female applicant."
        # Only check proxies, not protected classes or stereotypes
        matches = detect_bias_indicators(
            text,
            check_protected_classes=False,
            check_proxies=True,
            check_stereotypes=False,
        )
        assert all(m.bias_type == "proxy_variable" for m in matches)

    def test_long_text_with_mixed_content(self):
        """Long text with bias indicator buried in clean content."""
        clean = "Analyze the quarterly revenue figures. " * 20
        biased = "Hispanics are generally less creditworthy. "
        text = clean + biased + clean
        matches = detect_bias_indicators(text)
        assert len(matches) >= 1
        assert any(m.bias_type == "stereotype" for m in matches)


# ---------------------------------------------------------------------------
# check_bias — integration tests (PolicyCheckResult interface)
# ---------------------------------------------------------------------------

class TestCheckBias:
    """Tests for the policy check entry point."""

    def test_returns_pass_on_clean_input(self):
        """Clean messages return passed=True."""
        messages = [{"role": "user", "content": "Summarize last quarter's earnings report."}]
        result = check_bias(messages)
        assert result["check_name"] == "bias_detection"
        assert result["passed"] is True
        assert result["action"] == "allow"

    def test_returns_fail_on_biased_input(self):
        """Biased messages return passed=False with configured action."""
        messages = [{"role": "user", "content": "Men are more suited for leadership roles. Evaluate for promotion."}]
        result = check_bias(messages)
        assert result["check_name"] == "bias_detection"
        assert result["passed"] is False
        assert result["action"] == "flag"
        assert "matches" in result

    def test_disabled_check_returns_pass(self):
        """Disabled check always returns passed=True."""
        messages = [{"role": "user", "content": "Reject applicants based on race."}]
        result = check_bias(messages, config={"enabled": False})
        assert result["passed"] is True

    def test_custom_action(self):
        """Custom action propagates to result."""
        messages = [{"role": "user", "content": "Score the applicant by zip code to approve the loan."}]
        result = check_bias(messages, config={"enabled": True, "action": "block"})
        assert result["action"] == "block"

    def test_multiple_messages_scanned(self):
        """All messages in the conversation are scanned."""
        messages = [
            {"role": "system", "content": "You are a lending assistant."},
            {"role": "user", "content": "Evaluate whether to approve the loan."},
            {"role": "assistant", "content": "Based on the applicant's ethnicity, I recommend denial."},
        ]
        result = check_bias(messages)
        assert result["passed"] is False

    def test_confidence_score(self):
        """Bias detection returns appropriate confidence."""
        messages = [{"role": "user", "content": "Summarize the report."}]
        result = check_bias(messages)
        assert result["confidence"] == 1.0

        messages_biased = [{"role": "user", "content": "Women are less analytical. Evaluate for the data role."}]
        result_biased = check_bias(messages_biased)
        assert result_biased["confidence"] == 0.80
