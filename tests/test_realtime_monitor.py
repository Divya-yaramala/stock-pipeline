from unittest.mock import MagicMock, patch

from ingestion.realtime_monitor import (
    check_api_availability,
    check_error_rate,
    check_pipeline_lag,
    run_monitor_cycle,
)


def test_check_api_availability_structure():
    mock_ticker = MagicMock()
    mock_ticker.fast_info.last_price = 150.0
    with patch("ingestion.realtime_monitor.yf.Ticker", return_value=mock_ticker):
        result = check_api_availability("AAPL")
    assert "available" in result
    assert "latency_ms" in result
    assert result["ticker"] == "AAPL"
    assert result["available"] is True


def test_check_api_availability_failure():
    with patch("ingestion.realtime_monitor.yf.Ticker", side_effect=Exception("timeout")):
        result = check_api_availability("AAPL")
    assert result["available"] is False
    assert "latency_ms" in result


def test_check_pipeline_lag_acceptable():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {"Contents": []}
    with patch("ingestion.realtime_monitor.boto3.client", return_value=mock_s3):
        result = check_pipeline_lag("test-bucket", "AAPL")
    assert "lag_minutes" in result
    assert "acceptable" in result
    assert result["ticker"] == "AAPL"
    assert result["lag_minutes"] == 999.0
    assert result["acceptable"] is False


def test_check_error_rate_structure():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.side_effect = [
        {"KeyCount": 1},
        {"KeyCount": 20},
    ]
    with patch("ingestion.realtime_monitor.boto3.client", return_value=mock_s3):
        result = check_error_rate("test-bucket", "2026-07-11")
    assert "error_rate_pct" in result
    assert "acceptable" in result
    assert isinstance(result["error_rate_pct"], float)


def test_run_monitor_cycle_structure():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {"Contents": [], "KeyCount": 0}
    mock_s3.put_object.return_value = {}
    mock_ticker = MagicMock()
    mock_ticker.fast_info.last_price = 150.0
    with patch("ingestion.realtime_monitor.boto3.client", return_value=mock_s3):
        with patch("ingestion.realtime_monitor.yf.Ticker", return_value=mock_ticker):
            result = run_monitor_cycle("test-bucket", tickers=["AAPL"])
    assert "checks_run" in result
    assert "issues_found" in result
    assert "results" in result
    assert result["checks_run"] > 0
