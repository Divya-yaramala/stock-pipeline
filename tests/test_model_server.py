import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from ingestion.model_server import (
    get_model_serving_stats,
    load_model_from_registry,
    log_prediction_request,
    run_model_serving_check,
    serve_prediction,
)


def test_load_model_from_registry_success():
    payload = {"model_name": "price_predictor", "model_version": "v1.0", "status": "production"}
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(payload).encode("utf-8"))}
    with patch("ingestion.model_server.boto3.client", return_value=mock_s3):
        result = load_model_from_registry("price_predictor", "v1.0", "test-bucket")
    assert "model_name" in result
    assert result["model_name"] == "price_predictor"


def test_serve_prediction_structure():
    metadata = {
        "model_name": "price_predictor",
        "model_version": "v1.0",
        "model_metrics": {"f1": 0.88},
    }
    with patch("ingestion.model_server.get_production_model", return_value=metadata):
        result = serve_prediction("price_predictor", "AAPL", {"close": 150.0}, "test-bucket")
    assert "prediction" in result
    assert "confidence" in result
    assert result["ticker"] == "AAPL"


def test_log_prediction_request_success():
    mock_s3 = MagicMock()
    with patch("ingestion.model_server.boto3.client", return_value=mock_s3):
        result = log_prediction_request(
            "AAPL",
            {"close": 150.0},
            {"prediction": 151.5, "confidence": 0.88},
            "test-bucket",
        )
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_get_model_serving_stats_structure():
    entry = {
        "ticker": "AAPL",
        "features": {"close": 150.0},
        "prediction": {"ticker": "AAPL", "prediction": 151.5, "confidence": 0.88},
        "logged_at": "2026-06-20T00:00:00+00:00",
    }
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "models/serving/2026/06/20/AAPL_123.json"}]
    }
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps(entry).encode("utf-8")
    mock_s3.get_object.return_value = {"Body": mock_body}
    with patch("ingestion.model_server.boto3.client", return_value=mock_s3):
        result = get_model_serving_stats("test-bucket", "2026-06-20")
    assert "total_requests" in result
    assert result["total_requests"] == 1


def test_run_model_serving_check_completes():
    metadata = {"model_name": "anomaly_detector", "model_version": "v1.0", "status": "production"}
    with patch("ingestion.model_server.get_production_model", return_value=metadata):
        run_model_serving_check()
