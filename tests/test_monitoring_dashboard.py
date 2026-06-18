import json
from unittest.mock import MagicMock, patch

from ingestion.monitoring_dashboard import (
    generate_dashboard_html,
    get_pipeline_kpis,
    get_ticker_health,
    get_trend_data,
    run_dashboard_update,
)


def _make_s3_body(data: dict) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode()
    return body


def test_get_pipeline_kpis_structure():
    payload = {"success_rate_pct": 95.0, "quality_score_pct": 88.0, "total_runs": 5}
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": _make_s3_body(payload)}
    with patch("ingestion.monitoring_dashboard.boto3.client", return_value=mock_s3):
        kpis = get_pipeline_kpis("test-bucket", "2026-06-18")
    assert "success_rate_pct" in kpis
    assert kpis["success_rate_pct"] == 95.0


def test_get_ticker_health_statuses():
    def s3_side_effect(Bucket, Key):
        ticker = Key.split("/")[-1].replace(".json", "")
        scores = {"AAPL": 95.0, "MSFT": 75.0, "GOOGL": 50.0, "AMZN": 92.0, "TSLA": 65.0}
        quality = scores.get(ticker, 80.0)
        return {"Body": _make_s3_body({"quality_score": quality, "last_updated": "2026-06-18"})}

    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = s3_side_effect
    with patch("ingestion.monitoring_dashboard.boto3.client", return_value=mock_s3):
        health = get_ticker_health("test-bucket", "2026-06-18")

    assert health["AAPL"]["status"] == "healthy"
    assert health["MSFT"]["status"] == "warning"
    assert health["GOOGL"]["status"] == "critical"


def test_generate_dashboard_html_contains_kpis():
    kpis = {
        "success_rate_pct": 97.5,
        "quality_score_pct": 91.0,
        "sla_met_pct": 100.0,
        "anomaly_count": 2,
        "dlq_count": 0,
        "total_runs": 10,
    }
    ticker_health = {
        "AAPL": {"status": "healthy", "last_updated": "2026-06-18", "quality_score": 95.0}
    }
    trends = [{"date": "2026-06-18", "success_rate_pct": 97.5, "quality_score_pct": 91.0}]
    html = generate_dashboard_html(kpis, ticker_health, trends)
    assert "97.5" in html
    assert "success_rate_pct" not in html or "97.5" in html
    assert "AAPL" in html


def test_get_trend_data_returns_list():
    payload = {"success_rate_pct": 90.0, "quality_score_pct": 85.0}
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": _make_s3_body(payload)}
    with patch("ingestion.monitoring_dashboard.boto3.client", return_value=mock_s3):
        trends = get_trend_data("test-bucket", days=7)
    assert isinstance(trends, list)
    assert len(trends) == 7


def test_run_dashboard_update_success():
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = Exception("not found")
    mock_s3.put_object.return_value = {}
    with patch("ingestion.monitoring_dashboard.boto3.client", return_value=mock_s3):
        path = run_dashboard_update("test-bucket")
    assert isinstance(path, str)
    assert path.startswith("s3://")
