import json
from unittest.mock import MagicMock, patch

from ingestion.self_service_analytics import (
    build_custom_report,
    compare_metrics,
    get_metric_trends,
    list_available_metrics,
)


def _make_s3_body(data: dict) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return body


def test_list_available_metrics_count():
    result = list_available_metrics()
    assert isinstance(result, list)
    assert len(result) == 8


def test_list_available_metrics_structure():
    result = list_available_metrics()
    for metric in result:
        assert "metric_id" in metric
        assert "name" in metric
        assert "category" in metric


def test_compare_metrics_structure():
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": _make_s3_body({"value": 92.5})}
    with patch("ingestion.self_service_analytics.boto3.client", return_value=mock_client):
        result = compare_metrics(
            metric_id="M006",
            tickers=["AAPL", "MSFT"],
            date="2026-07-27",
            bucket="test-bucket",
        )
    assert isinstance(result, dict)
    assert "by_ticker" in result
    assert "leader" in result
    assert "metric_id" in result


def test_build_custom_report_structure():
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": _make_s3_body({"value": 88.0})}
    mock_client.put_object.return_value = {}
    with patch("ingestion.self_service_analytics.boto3.client", return_value=mock_client):
        result = build_custom_report(
            metrics=["M001", "M006"],
            tickers=["AAPL", "MSFT"],
            date="2026/07/27",
            bucket="test-bucket",
        )
    assert isinstance(result, dict)
    assert "AAPL" in result
    assert "MSFT" in result


def test_get_metric_trends_structure():
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": _make_s3_body({"value": 90.0})}
    with patch("ingestion.self_service_analytics.boto3.client", return_value=mock_client):
        result = get_metric_trends(
            metric_id="M006",
            ticker="AAPL",
            days=7,
            bucket="test-bucket",
        )
    assert isinstance(result, dict)
    assert "trend" in result
    assert "avg" in result
    assert "min" in result
    assert "max" in result
