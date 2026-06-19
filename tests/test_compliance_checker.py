import json
from unittest.mock import MagicMock, patch

from ingestion.compliance_checker import (
    check_audit_logs_present,
    check_no_pii_in_raw,
    run_compliance_check,
)


def test_run_compliance_check_structure():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {"Contents": [{"Key": "some/key"}]}
    with (
        patch("ingestion.compliance_checker.check_encryption", return_value=True),
        patch(
            "ingestion.compliance_checker.check_no_pii_in_raw",
            return_value={"compliant": True, "violations": []},
        ),
        patch("ingestion.compliance_checker.check_audit_logs_present", return_value=True),
        patch("ingestion.compliance_checker.boto3.client", return_value=mock_s3),
    ):
        result = run_compliance_check("test-bucket")
    assert "compliant" in result
    assert "score_pct" in result


def test_check_no_pii_compliant():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "raw/stocks/2026/06/19/AAPL.json"}]
    }
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps({"ticker": "AAPL", "close": 150.0}).encode("utf-8")
    mock_s3.get_object.return_value = {"Body": mock_body}
    with patch("ingestion.compliance_checker.boto3.client", return_value=mock_s3):
        result = check_no_pii_in_raw("test-bucket", "2026-06-19")
    assert result["compliant"] is True


def test_check_no_pii_violation():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "raw/stocks/2026/06/19/AAPL.json"}]
    }
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps(
        {"ticker": "AAPL", "email": "user@example.com"}
    ).encode("utf-8")
    mock_s3.get_object.return_value = {"Body": mock_body}
    with patch("ingestion.compliance_checker.boto3.client", return_value=mock_s3):
        result = check_no_pii_in_raw("test-bucket", "2026-06-19")
    assert result["compliant"] is False


def test_check_audit_logs_present_true():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "governance/audit/2026/06/19/123456.json"}]
    }
    with patch("ingestion.compliance_checker.boto3.client", return_value=mock_s3):
        assert check_audit_logs_present("test-bucket", "2026-06-19") is True


def test_check_audit_logs_present_false():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {"Contents": []}
    with patch("ingestion.compliance_checker.boto3.client", return_value=mock_s3):
        assert check_audit_logs_present("test-bucket", "2026-06-19") is False
