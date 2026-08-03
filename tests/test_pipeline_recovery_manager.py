import json
from unittest.mock import MagicMock, patch

from ingestion.pipeline_recovery_manager import (
    calculate_pipeline_resilience,
    create_checkpoint,
    handle_step_failure,
    load_latest_checkpoint,
)


def test_create_checkpoint_returns_id():
    state = {"ticker": "AAPL", "processed": 3}
    with patch("ingestion.pipeline_recovery_manager.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        checkpoint_id = create_checkpoint(
            "daily_pipeline", "anomaly_detection", state, "test-bucket"
        )
    assert isinstance(checkpoint_id, str)
    assert "daily_pipeline" in checkpoint_id
    mock_s3.put_object.assert_called_once()


def test_load_latest_checkpoint_found():
    checkpoint_data = {
        "checkpoint_id": "daily_pipeline_validate_20260803",
        "state": {"ticker": "AAPL", "processed": 3},
    }
    with patch("ingestion.pipeline_recovery_manager.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.get_paginator.return_value.paginate.return_value = [
            {"Contents": [{"Key": "recovery/checkpoints/daily_pipeline/validate_20260803.json"}]}
        ]
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: json.dumps(checkpoint_data).encode())
        }
        result = load_latest_checkpoint("daily_pipeline", "validate", "test-bucket")
    assert result is not None
    assert "state" in result


def test_load_latest_checkpoint_not_found():
    with patch("ingestion.pipeline_recovery_manager.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.get_paginator.return_value.paginate.return_value = [{"Contents": []}]
        result = load_latest_checkpoint("daily_pipeline", "validate", "test-bucket")
    assert result is None


def test_handle_step_failure_retry():
    with patch("ingestion.pipeline_recovery_manager.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        result = handle_step_failure(
            "daily_pipeline", "snowflake_sync", "Connection timeout", "retry", "test-bucket"
        )
    assert result["should_continue"] is True
    assert result["strategy"] == "retry"


def test_calculate_pipeline_resilience_structure():
    recovery_history = [
        {"strategy": "retry", "step_name": "snowflake_sync", "error": "timeout"},
        {"strategy": "manual", "step_name": "anomaly_detection", "error": "model error"},
        {"strategy": "skip", "step_name": "predict", "error": "API limit"},
    ]
    result = calculate_pipeline_resilience(recovery_history)
    assert "auto_recovery_rate_pct" in result
    assert "manual_interventions" in result
    assert "most_common_failure" in result
    assert result["manual_interventions"] == 1
