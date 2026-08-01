import json
from unittest.mock import MagicMock, patch

import pytest

from ingestion.model_deployment_manager import (
    create_deployment,
    get_active_deployment,
    list_deployments,
)


def _make_s3_mock(pages=None):
    mock_s3 = MagicMock()
    mock_s3.get_paginator.return_value.paginate.return_value = pages or [{"Contents": []}]
    return mock_s3


def test_create_deployment_success():
    with patch("ingestion.model_deployment_manager.boto3.client") as mock_client:
        mock_client.return_value = _make_s3_mock()
        dep_id = create_deployment(
            model_name="anomaly_detector",
            model_version="v1.0",
            environment="development",
            metrics={"accuracy": 0.85},
            bucket="test-bucket",
        )
    assert isinstance(dep_id, str)
    assert len(dep_id) > 0


def test_create_deployment_invalid_environment():
    with pytest.raises(ValueError):
        create_deployment(
            model_name="anomaly_detector",
            model_version="v1.0",
            environment="invalid_env",
            metrics={"accuracy": 0.85},
            bucket="test-bucket",
        )


def test_get_active_deployment_found():
    deployment = {
        "deployment_id": "abc123",
        "model_name": "anomaly_detector",
        "model_version": "v1.0",
        "environment": "production",
        "metrics": {"accuracy": 0.85},
        "status": "active",
        "deployed_at": "2026-08-01T10:00:00",
    }
    with patch("ingestion.model_deployment_manager.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.get_paginator.return_value.paginate.return_value = [
            {"Contents": [{"Key": "deployments/production/anomaly_detector/abc123.json"}]}
        ]
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: json.dumps(deployment).encode())
        }
        mock_client.return_value = mock_s3
        result = get_active_deployment("anomaly_detector", "production", "test-bucket")
    assert isinstance(result, dict)
    assert "model_name" in result


def test_get_active_deployment_not_found():
    with patch("ingestion.model_deployment_manager.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.get_paginator.side_effect = Exception("S3 error")
        mock_client.return_value = mock_s3
        result = get_active_deployment("anomaly_detector", "production", "test-bucket")
    assert result is None


def test_list_deployments_returns_list():
    deployment = {
        "deployment_id": "abc123",
        "model_name": "anomaly_detector",
        "status": "active",
    }
    with patch("ingestion.model_deployment_manager.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.get_paginator.return_value.paginate.return_value = [
            {"Contents": [{"Key": "deployments/staging/anomaly_detector/abc123.json"}]}
        ]
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: json.dumps(deployment).encode())
        }
        mock_client.return_value = mock_s3
        result = list_deployments("staging", "test-bucket")
    assert isinstance(result, list)
