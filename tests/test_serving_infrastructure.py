import json
from unittest.mock import MagicMock, patch

from ingestion.serving_infrastructure import (
    create_serving_endpoint,
    get_endpoint_metrics,
    health_check_endpoint,
    run_infrastructure_check,
    scale_endpoint,
)

_SAMPLE_CONFIG = {
    "endpoint_id": "abc123def456",
    "model_name": "anomaly_detector",
    "environment": "production",
    "port": 8080,
    "status": "running",
    "replicas": 1,
    "created_at": "2026-08-01T10:00:00",
}

_SAMPLE_METRICS = {
    "requests_per_minute": 120.5,
    "avg_latency_ms": 18.3,
    "error_rate_pct": 0.5,
    "p95_latency_ms": 42.1,
}


def test_create_serving_endpoint_structure():
    with patch("ingestion.serving_infrastructure.boto3.client") as mock_client:
        mock_client.return_value = MagicMock()
        result = create_serving_endpoint("anomaly_detector", "production", 8080, "test-bucket")
    assert isinstance(result, dict)
    assert "endpoint_id" in result


def test_health_check_endpoint_healthy():
    result = health_check_endpoint(_SAMPLE_CONFIG)
    assert isinstance(result, dict)
    assert "healthy" in result
    assert result["healthy"] is True


def test_scale_endpoint_success():
    with patch("ingestion.serving_infrastructure.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.get_paginator.return_value.paginate.return_value = [
            {"Contents": [{"Key": "serving/endpoints/production/anomaly_detector.json"}]}
        ]
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: json.dumps(_SAMPLE_CONFIG).encode())
        }
        mock_client.return_value = mock_s3
        result = scale_endpoint("abc123def456", 3, "test-bucket")
    assert result is True


def test_get_endpoint_metrics_structure():
    with patch("ingestion.serving_infrastructure.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: json.dumps(_SAMPLE_METRICS).encode())
        }
        mock_client.return_value = mock_s3
        result = get_endpoint_metrics("abc123def456", "test-bucket", "2026/08/01")
    assert isinstance(result, dict)
    assert "avg_latency_ms" in result


def test_run_infrastructure_check_structure():
    with patch("ingestion.serving_infrastructure.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.get_paginator.return_value.paginate.return_value = [{"Contents": []}]
        mock_client.return_value = mock_s3
        result = run_infrastructure_check("test-bucket")
    assert isinstance(result, dict)
    assert "total_endpoints" in result
