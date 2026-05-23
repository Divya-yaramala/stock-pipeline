from unittest.mock import MagicMock, patch

import pytest

from ingestion.pipeline_monitor import (
    generate_daily_report,
    get_pipeline_metrics,
    record_pipeline_run,
)


def test_record_pipeline_run_success():
    with patch("ingestion.pipeline_monitor.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        result = record_pipeline_run("fetch", "AAPL", "success", 1.23, "test-bucket")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_record_pipeline_run_failure():
    with patch("ingestion.pipeline_monitor.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = Exception("S3 error")
        mock_boto3.client.return_value = mock_s3
        result = record_pipeline_run("fetch", "AAPL", "success", 1.23, "test-bucket")
    assert result is False


def test_generate_daily_report_structure():
    sample_metrics = [
        {"step": "fetch", "ticker": "AAPL", "status": "success", "duration_seconds": 2.0},
        {"step": "fetch", "ticker": "MSFT", "status": "success", "duration_seconds": 3.0},
        {"step": "anomaly", "ticker": "AAPL", "status": "failed", "duration_seconds": 1.0},
    ]
    with patch("ingestion.pipeline_monitor.get_pipeline_metrics", return_value=sample_metrics):
        report = generate_daily_report("test-bucket", "2026/05/23")

    required_keys = {
        "date",
        "total_runs",
        "successful_runs",
        "failed_runs",
        "success_rate_pct",
        "avg_duration_seconds",
        "slowest_step",
        "fastest_step",
    }
    assert required_keys.issubset(report.keys())
    assert report["total_runs"] == 3
    assert report["successful_runs"] == 2
    assert report["failed_runs"] == 1
    assert report["success_rate_pct"] == pytest.approx(66.67, rel=0.01)


def test_get_pipeline_metrics_empty():
    with patch("ingestion.pipeline_monitor.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {"Contents": []}
        mock_boto3.client.return_value = mock_s3
        result = get_pipeline_metrics("test-bucket", "2026/05/23")
    assert result == []
