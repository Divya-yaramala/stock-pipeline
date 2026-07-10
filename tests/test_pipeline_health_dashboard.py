from typing import Any, Dict
from unittest.mock import MagicMock, patch

from ingestion.pipeline_health_dashboard import (
    generate_health_html,
    get_pipeline_summary,
    get_system_health,
    save_health_dashboard,
)

SAMPLE_SUMMARY: Dict[str, Any] = {
    "date": "2026-07-10",
    "total_tickers": 5,
    "successful_tickers": 4,
    "failed_tickers": 1,
    "avg_quality_score": 87.5,
    "total_anomalies": 3,
    "total_predictions": 25,
    "pipeline_duration_minutes": 12.4,
}

SAMPLE_TICKER_STATUS: Dict[str, Any] = {
    "AAPL": {"status": "success", "quality_score": 92.0, "anomalies": 1},
    "MSFT": {"status": "success", "quality_score": 88.0, "anomalies": 0},
}

SAMPLE_SYSTEM_HEALTH: Dict[str, Any] = {
    "overall_health": "healthy",
    "score": 100.0,
    "issues": [],
}


def test_get_pipeline_summary_structure():
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = Exception("no file")
    with patch("ingestion.pipeline_health_dashboard.boto3.client", return_value=mock_s3):
        result = get_pipeline_summary("test-bucket", "2026-07-10")
    assert "total_tickers" in result
    assert result["date"] == "2026-07-10"


def test_generate_health_html_contains_date():
    html = generate_health_html(SAMPLE_SUMMARY, SAMPLE_TICKER_STATUS, SAMPLE_SYSTEM_HEALTH)
    assert "Health Dashboard" in html
    assert "2026-07-10" in html


def test_generate_health_html_contains_tickers():
    html = generate_health_html(SAMPLE_SUMMARY, SAMPLE_TICKER_STATUS, SAMPLE_SYSTEM_HEALTH)
    assert "AAPL" in html
    assert "MSFT" in html


def test_save_health_dashboard_success():
    mock_s3 = MagicMock()
    with patch("ingestion.pipeline_health_dashboard.boto3.client", return_value=mock_s3):
        url = save_health_dashboard("<html></html>", "test-bucket", "2026-07-10")
    assert isinstance(url, str)
    assert "test-bucket" in url
    mock_s3.put_object.assert_called_once()


def test_get_system_health_structure():
    with patch("ingestion.pipeline_health_dashboard.boto3.client"):
        result = get_system_health("test-bucket")
    assert "overall_health" in result
    assert "score" in result
    assert "issues" in result
    assert result["overall_health"] in ("healthy", "warning", "critical")
