import json
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from ingestion.retraining_trigger import (
    check_retraining_schedule,
    create_retraining_job,
    get_pending_retraining_jobs,
    mark_job_complete,
)


def test_check_retraining_schedule_triggered():
    last_trained = (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d")
    payload = json.dumps({"last_trained_date": last_trained}).encode("utf-8")
    with patch("ingestion.retraining_trigger.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.return_value = {"Body": BytesIO(payload)}
        result = check_retraining_schedule(
            "anomaly_detector", "test-bucket", max_days_since_training=30
        )
    assert result["schedule_triggered"] is True


def test_check_retraining_schedule_not_triggered():
    last_trained = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    payload = json.dumps({"last_trained_date": last_trained}).encode("utf-8")
    with patch("ingestion.retraining_trigger.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.return_value = {"Body": BytesIO(payload)}
        result = check_retraining_schedule(
            "anomaly_detector", "test-bucket", max_days_since_training=30
        )
    assert result["schedule_triggered"] is False


def test_create_retraining_job_success():
    with patch("ingestion.retraining_trigger.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        job_id = create_retraining_job("AAPL", "drift_detected", "test-bucket")
    assert isinstance(job_id, str)
    assert len(job_id) > 0
    mock_s3.put_object.assert_called_once()


def test_get_pending_retraining_jobs_structure():
    job_payload: Dict[str, Any] = {
        "ticker": "AAPL",
        "reason": "drift",
        "status": "pending",
        "created_at": "2026-06-30T00:00:00",
    }
    with patch("ingestion.retraining_trigger.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "models/retraining_jobs/2026/06/30/AAPL_123.json"}]
        }
        mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(job_payload).encode("utf-8"))}
        result = get_pending_retraining_jobs("test-bucket")
    assert isinstance(result, list)


def test_mark_job_complete_success():
    job_payload: Dict[str, Any] = {
        "ticker": "AAPL",
        "reason": "drift",
        "status": "pending",
        "created_at": "2026-06-30T00:00:00",
    }
    with patch("ingestion.retraining_trigger.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(job_payload).encode("utf-8"))}
        result = mark_job_complete(
            "models/retraining_jobs/2026/06/30/AAPL_123.json", "test-bucket", success=True
        )
    assert result is True
