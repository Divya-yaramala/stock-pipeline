import json
import re
from io import BytesIO
from unittest.mock import MagicMock, patch

from ingestion.experiment_tracker import end_experiment, log_metrics, start_experiment


def test_start_experiment_success():
    with patch("ingestion.experiment_tracker.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        run_id = start_experiment(
            "anomaly_tuning", "anomaly_detector", {"contamination": 0.05}, "test-bucket"
        )
    assert isinstance(run_id, str)
    assert "anomaly_tuning" in run_id


def test_log_metrics_success():
    run_id = "anomaly_tuning_20260607_120000_000000"
    record = {"run_id": run_id, "experiment_name": "anomaly_tuning", "metrics": {}}
    key = f"experiments/2026/06/07/anomaly_tuning/{run_id}.json"
    with patch("ingestion.experiment_tracker.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {"Contents": [{"Key": key}]}
        mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(record).encode("utf-8"))}
        result = log_metrics(run_id, {"f1": 0.92}, "test-bucket")
    assert result is True


def test_end_experiment_success():
    run_id = "anomaly_tuning_20260607_120000_000000"
    record = {
        "run_id": run_id,
        "experiment_name": "anomaly_tuning",
        "metrics": {"f1": 0.92},
        "status": "running",
    }
    key = f"experiments/2026/06/07/anomaly_tuning/{run_id}.json"
    with patch("ingestion.experiment_tracker.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {"Contents": [{"Key": key}]}
        mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(record).encode("utf-8"))}
        result = end_experiment(run_id, "completed", "test-bucket")
    assert result is True


def test_end_experiment_failure():
    with patch("ingestion.experiment_tracker.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.list_objects_v2.side_effect = Exception("S3 connection failed")
        result = end_experiment("bad_run_id", "completed", "test-bucket")
    assert result is False


def test_start_experiment_correct_path():
    with patch("ingestion.experiment_tracker.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        start_experiment(
            "anomaly_tuning", "anomaly_detector", {"contamination": 0.05}, "test-bucket"
        )
    call_kwargs = mock_s3.put_object.call_args.kwargs
    key = call_kwargs["Key"]
    assert re.match(r"experiments/\d{4}/\d{2}/\d{2}/", key)
