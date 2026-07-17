"""Tests for the 6 new REST API endpoints added in Day 68."""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app


def _mock_s3_body(data: Any) -> MagicMock:
    body = MagicMock()
    body.read.return_value = __import__("json").dumps(data).encode("utf-8")
    return body


def test_quality_gates_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/quality-gates/AAPL")
    assert response.status_code == 200
    data: Dict[str, Any] = response.json()
    assert isinstance(data, dict)


def test_feature_flags_endpoint() -> None:
    mock_client = MagicMock()
    mock_client.get_object.side_effect = Exception("no s3")

    with patch("ingestion.feature_flag_manager.boto3.client", return_value=mock_client):
        client = TestClient(app)
        response = client.get("/feature-flags")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_data_products_endpoint() -> None:
    mock_client = MagicMock()
    paginator = MagicMock()
    paginator.paginate.return_value = [{"Contents": []}]
    mock_client.get_paginator.return_value = paginator

    with patch("ingestion.data_product_manager.boto3.client", return_value=mock_client):
        client = TestClient(app)
        response = client.get("/data-products")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_pipeline_health_endpoint() -> None:
    mock_client = MagicMock()
    mock_client.get_object.side_effect = Exception("no s3")

    with patch("ingestion.sla_reporter.boto3.client", return_value=mock_client):
        with patch("ingestion.resource_manager.boto3.client", return_value=mock_client):
            client = TestClient(app)
            response = client.get("/pipeline-health")

    assert response.status_code == 200
    data: Dict[str, Any] = response.json()
    assert "health_score" in data


def test_api_docs_summary_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api-docs/summary")
    assert response.status_code == 200
    data: Dict[str, Any] = response.json()
    assert "total_endpoints" in data
    assert data["total_endpoints"] == 13


def test_api_docs_by_category() -> None:
    client = TestClient(app)
    response = client.get("/api-docs/endpoints/ml")
    assert response.status_code == 200
    results: List[Dict[str, Any]] = response.json()
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(ep["category"] == "ml" for ep in results)
