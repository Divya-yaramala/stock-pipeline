import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from ingestion.model_registry import (
    get_model_metadata,
    get_production_model,
    promote_model,
    register_model,
)


def test_register_model_success():
    with patch("ingestion.model_registry.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        model_id = register_model(
            "anomaly_detector", "v1.0.0", {"n_estimators": 100}, {"f1": 0.92}, "test-bucket"
        )
    assert isinstance(model_id, str)
    assert len(model_id) == 32


def test_register_model_correct_path():
    with patch("ingestion.model_registry.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        register_model(
            "anomaly_detector", "v1.0.0", {"n_estimators": 100}, {"f1": 0.92}, "test-bucket"
        )
    call_kwargs = mock_s3.put_object.call_args.kwargs
    assert "models/registry/" in call_kwargs["Key"]
    assert "anomaly_detector" in call_kwargs["Key"]
    assert "v1.0.0" in call_kwargs["Key"]


def test_get_model_metadata_success():
    payload = {
        "model_id": "abc123",
        "model_name": "anomaly_detector",
        "model_version": "v1.0.0",
        "status": "active",
    }
    with patch("ingestion.model_registry.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(payload).encode("utf-8"))}
        result = get_model_metadata("anomaly_detector", "v1.0.0", "test-bucket")
    assert isinstance(result, dict)
    assert "model_name" in result
    assert result["model_name"] == "anomaly_detector"


def test_promote_model_success():
    payload = {"model_name": "anomaly_detector", "model_version": "v1.0.0", "status": "active"}
    with patch("ingestion.model_registry.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(payload).encode("utf-8"))}
        result = promote_model("anomaly_detector", "v1.0.0", "test-bucket", "production")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_get_production_model_success():
    payload = {
        "model_name": "anomaly_detector",
        "model_version": "v1.0.0",
        "status": "production",
    }
    with patch("ingestion.model_registry.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            "CommonPrefixes": [{"Prefix": "models/registry/anomaly_detector/v1.0.0/"}]
        }
        mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(payload).encode("utf-8"))}
        result = get_production_model("anomaly_detector", "test-bucket")
    assert isinstance(result, dict)
    assert result.get("status") == "production"
