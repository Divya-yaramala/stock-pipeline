import json
from unittest.mock import MagicMock, patch

from ingestion.sla_reporter import (
    generate_sla_report,
    get_sla_trend,
    record_sla_completion,
)


def test_record_sla_completion_met():
    mock_s3 = MagicMock()
    with patch("ingestion.sla_reporter.boto3.client", return_value=mock_s3):
        result = record_sla_completion("SLA001", "2026-07-11T06:30:00", "test-bucket", "2026-07-11")
    assert result is True
    mock_s3.put_object.assert_called_once()
    body = json.loads(mock_s3.put_object.call_args[1]["Body"])
    assert body["met"] is True


def test_record_sla_completion_missed():
    mock_s3 = MagicMock()
    with patch("ingestion.sla_reporter.boto3.client", return_value=mock_s3):
        result = record_sla_completion("SLA001", "2026-07-11T09:00:00", "test-bucket", "2026-07-11")
    assert result is True
    body = json.loads(mock_s3.put_object.call_args[1]["Body"])
    assert body["met"] is False


def test_generate_sla_report_structure():
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = Exception("not found")
    mock_s3.put_object.return_value = {}
    with patch("ingestion.sla_reporter.boto3.client", return_value=mock_s3):
        result = generate_sla_report("test-bucket", "2026-07-11")
    assert "compliance_pct" in result
    assert "by_sla" in result
    assert "date" in result


def test_generate_sla_report_full_compliance():
    mock_s3 = MagicMock()
    met_record = json.dumps({"met": True, "completed_at": "2026-07-11T06:00:00"}).encode()
    mock_body = MagicMock()
    mock_body.read.return_value = met_record
    mock_s3.get_object.return_value = {"Body": mock_body}
    mock_s3.put_object.return_value = {}
    with patch("ingestion.sla_reporter.boto3.client", return_value=mock_s3):
        result = generate_sla_report("test-bucket", "2026-07-11")
    assert result["compliance_pct"] == 100.0


def test_get_sla_trend_structure():
    mock_s3 = MagicMock()
    day_record = json.dumps({"compliance_pct": 100.0}).encode()
    mock_body = MagicMock()
    mock_body.read.return_value = day_record
    mock_s3.get_object.return_value = {"Body": mock_body}
    with patch("ingestion.sla_reporter.boto3.client", return_value=mock_s3):
        result = get_sla_trend("test-bucket", days=7)
    assert "avg_compliance_pct" in result
    assert "trend" in result
    assert "daily" in result
    assert result["avg_compliance_pct"] == 100.0
