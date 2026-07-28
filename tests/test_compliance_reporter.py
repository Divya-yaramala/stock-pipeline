import json
from unittest.mock import MagicMock, patch

from ingestion.compliance_reporter import (
    calculate_compliance_trend,
    check_framework_compliance,
    generate_compliance_certificate,
    generate_compliance_report,
    get_compliance_history,
)


def _make_s3_body(data: dict) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return body


def test_check_framework_compliance_structure():
    mock_client = MagicMock()
    with patch("ingestion.compliance_reporter.boto3.client", return_value=mock_client):
        result = check_framework_compliance("CF004", "test-bucket", "2026-07-28")
    assert isinstance(result, dict)
    assert "framework" in result
    assert "score_pct" in result
    assert "passed" in result
    assert "failed" in result
    assert "compliant" in result


def test_generate_compliance_report_structure():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.compliance_reporter.boto3.client", return_value=mock_client):
        result = generate_compliance_report("test-bucket", "2026-07-28")
    assert isinstance(result, dict)
    assert "total_score_pct" in result
    assert "frameworks" in result
    assert "overall_compliant" in result
    assert "date" in result


def test_calculate_compliance_trend_structure():
    history = [
        {"total_score_pct": 75.0},
        {"total_score_pct": 80.0},
        {"total_score_pct": 85.0},
    ]
    result = calculate_compliance_trend(history)
    assert isinstance(result, dict)
    assert "trend" in result
    assert "avg_score" in result
    assert result["trend"] == "improving"


def test_generate_compliance_certificate_certified():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.compliance_reporter.boto3.client", return_value=mock_client):
        result = generate_compliance_certificate("CF004", "test-bucket", "2026-07-28")
    assert isinstance(result, dict)
    assert "certified" in result
    assert "framework" in result
    assert "certificate_id" in result
    if result["certified"]:
        assert len(result["certificate_id"]) > 0


def test_get_compliance_history_returns_list():
    report = {"date": "2026-07-28", "total_score_pct": 80.0, "overall_compliant": False}
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": _make_s3_body(report)}
    with patch("ingestion.compliance_reporter.boto3.client", return_value=mock_client):
        result = get_compliance_history("test-bucket", days=3)
    assert isinstance(result, list)
