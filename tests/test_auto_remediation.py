from typing import Any, Dict
from unittest.mock import MagicMock, patch

from ingestion.auto_remediation import (
    detect_issue,
    run_auto_remediation,
    trigger_remediation,
)

HEALTHY_METRICS: Dict[str, Any] = {
    "hours_since_update": 10.0,
    "completeness_pct": 95.0,
    "quality_score": 85.0,
    "anomaly_rate_pct": 5.0,
    "prediction_accuracy_pct": 80.0,
}

STALE_METRICS: Dict[str, Any] = {
    **HEALTHY_METRICS,
    "hours_since_update": 30.0,
}


def test_detect_issue_stale_data():
    issue = detect_issue(STALE_METRICS, "AAPL")
    assert issue == "stale_data"


def test_detect_issue_none():
    issue = detect_issue(HEALTHY_METRICS, "AAPL")
    assert issue is None


def test_trigger_remediation_success():
    mock_s3 = MagicMock()
    with patch("ingestion.auto_remediation.boto3.client", return_value=mock_s3):
        record = trigger_remediation("stale_data", "AAPL", "test-bucket")
    assert "action" in record
    assert record["action"] == "trigger_backfill"
    assert record["status"] == "triggered"


def test_run_auto_remediation_triggered():
    mock_s3 = MagicMock()
    with patch("ingestion.auto_remediation.boto3.client", return_value=mock_s3):
        result = run_auto_remediation("AAPL", STALE_METRICS, "test-bucket")
    assert result is not None
    assert result["issue"] == "stale_data"


def test_run_auto_remediation_none():
    result = run_auto_remediation("AAPL", HEALTHY_METRICS, "test-bucket")
    assert result is None
