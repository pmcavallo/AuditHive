"""Tests for the examiner simulation agent."""

import json
from unittest.mock import MagicMock, patch

import pytest

from audithive.examiner.agent import (
    ExaminerContext,
    ExaminerReportData,
    generate_examiner_report,
    _generate_static_report,
)


def _make_context(**overrides) -> ExaminerContext:
    defaults = dict(
        industry="ecommerce", jurisdictions=["california"], ai_use_cases=["customer_chatbot"],
        coverage_score=40.0, maturity_level="immature",
        applicable_regulations=[{"regulation": "CCPA", "jurisdiction": "california", "why": "test"}],
        missing_controls=[{"control": "ai_disclosure", "required_by": ["CCPA"], "fix": "Enable it", "effort": "one_click"}],
        gaps=[{"gap_type": "action_mismatch", "description": "test gap", "risk": "medium", "fix": "fix it", "effort": "one_click"}],
        four_questions={}, total_calls=100, total_blocked=5, total_flagged=10,
        violation_details=[], active_policies=[{"name": "Default"}],
    )
    defaults.update(overrides)
    return ExaminerContext(**defaults)


def test_static_report_valid_structure() -> None:
    ctx = _make_context()
    report = _generate_static_report(ctx)
    assert isinstance(report, ExaminerReportData)
    assert report.executive_summary
    assert report.risk_rating in ("high", "medium", "low")
    assert len(report.findings) > 0
    assert len(report.questions) > 0


def test_static_findings_have_all_fields() -> None:
    ctx = _make_context()
    report = _generate_static_report(ctx)
    for f in report.findings:
        assert f.title
        assert f.severity in ("critical", "high", "medium", "low")
        assert f.description
        assert f.evidence
        assert f.regulation
        assert f.remediation


def test_static_risk_rating_high_when_low_coverage() -> None:
    report = _generate_static_report(_make_context(coverage_score=30.0))
    assert report.risk_rating == "high"


def test_static_risk_rating_low_when_high_coverage() -> None:
    report = _generate_static_report(_make_context(coverage_score=85.0, missing_controls=[]))
    assert report.risk_rating == "low"


@pytest.mark.asyncio
async def test_agent_falls_back_when_no_api_key() -> None:
    """With no API key, agent uses static generation."""
    with patch("audithive.examiner.agent.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = ""
        report = await generate_examiner_report(_make_context())
    assert isinstance(report, ExaminerReportData)
    assert report.executive_summary


@pytest.mark.asyncio
async def test_agent_parses_llm_response() -> None:
    """Mock the Anthropic API and verify the agent parses the response."""
    fake_response = json.dumps({
        "executive_summary": "LLM-generated summary.",
        "risk_rating": "medium",
        "findings": [{"title": "F1", "severity": "high", "description": "D", "evidence": "E", "regulation": "R", "remediation": "Fix"}],
        "questions": ["Q1"],
        "recommendations": ["R1"],
    })

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=fake_response)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("audithive.examiner.agent.settings") as mock_settings, \
         patch("anthropic.Anthropic", return_value=mock_client):
        mock_settings.ANTHROPIC_API_KEY = "sk-ant-test"
        report = await generate_examiner_report(_make_context(), api_key="sk-ant-test")

    assert report.executive_summary == "LLM-generated summary."
    assert len(report.findings) == 1
    assert report.findings[0].title == "F1"
