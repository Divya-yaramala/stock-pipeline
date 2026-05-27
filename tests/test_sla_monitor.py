from unittest.mock import MagicMock, patch

from ingestion.sla_monitor import (
    get_sla_thresholds,
    record_sla_metric,
)


def test_record_sla_metric_met():
    with patch("ingestion.sla_monitor.boto3") as mock_boto3:
        mock_boto3.client.return_value = MagicMock()
        result = record_sla_metric("fetch", 30.0, 20.0, "test-bucket")
    assert result is True


def test_record_sla_metric_missed():
    captured = {}
    mock_s3 = MagicMock()

    def fake_put_object(**kwargs):
        import json

        captured["record"] = json.loads(kwargs["Body"])

    mock_s3.put_object.side_effect = fake_put_object
    with patch("ingestion.sla_monitor.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_s3
        record_sla_metric("fetch", 30.0, 45.0, "test-bucket")
    assert captured["record"]["sla_met"] is False


def test_get_sla_thresholds_has_all_steps():
    thresholds = get_sla_thresholds()
    expected_steps = {
        "fetch",
        "validation",
        "anomaly",
        "prediction",
        "insights",
        "snowflake_sync",
        "monitoring",
    }
    assert expected_steps.issubset(set(thresholds.keys()))


def test_record_sla_metric_success():
    with patch("ingestion.sla_monitor.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        result = record_sla_metric("validation", 10.0, 8.0, "test-bucket")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_record_sla_metric_failure():
    with patch("ingestion.sla_monitor.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = Exception("S3 error")
        mock_boto3.client.return_value = mock_s3
        result = record_sla_metric("anomaly", 60.0, 55.0, "test-bucket")
    assert result is False
