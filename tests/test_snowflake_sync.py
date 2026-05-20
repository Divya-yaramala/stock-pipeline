from unittest.mock import MagicMock, patch

from ingestion.snowflake_sync import (
    load_from_s3,
    run_snowflake_sync,
    sync_anomalies,
    sync_stock_prices,
)

_STOCK_DATA = {
    "Open": {"0": 150.0},
    "High": {"0": 155.0},
    "Low": {"0": 149.0},
    "Close": {"0": 153.0},
    "Volume": {"0": 1_000_000},
}

_ANOMALY_DATA = {
    "is_anomaly": {"0": False},
    "anomaly_score": {"0": 0.12},
}


@patch("ingestion.snowflake_sync.load_from_s3", return_value=_STOCK_DATA)
def test_sync_stock_prices_success(mock_load):
    mock_conn = MagicMock()
    result = sync_stock_prices(mock_conn, "AAPL", "2026/05/19")
    assert result is True


@patch("ingestion.snowflake_sync.load_from_s3", side_effect=Exception("S3 error"))
def test_sync_stock_prices_failure(mock_load):
    mock_conn = MagicMock()
    result = sync_stock_prices(mock_conn, "AAPL", "2026/05/19")
    assert result is False


@patch("ingestion.snowflake_sync.load_from_s3", return_value=_ANOMALY_DATA)
def test_sync_anomalies_success(mock_load):
    mock_conn = MagicMock()
    result = sync_anomalies(mock_conn, "AAPL", "2026/05/19")
    assert result is True


@patch("ingestion.snowflake_sync.load_from_s3", side_effect=Exception("S3 error"))
def test_sync_anomalies_failure(mock_load):
    mock_conn = MagicMock()
    result = sync_anomalies(mock_conn, "AAPL", "2026/05/19")
    assert result is False


@patch("ingestion.snowflake_sync.sync_insights", return_value=True)
@patch("ingestion.snowflake_sync.sync_predictions", return_value=True)
@patch("ingestion.snowflake_sync.sync_anomalies", return_value=True)
@patch("ingestion.snowflake_sync.sync_stock_prices", return_value=True)
@patch("ingestion.snowflake_sync._get_snowflake_connection")
def test_run_snowflake_sync_calls_all_tickers(
    mock_get_conn, mock_prices, mock_anomalies, mock_preds, mock_insights
):
    run_snowflake_sync()
    assert mock_prices.call_count == 5
    assert mock_anomalies.call_count == 5
    assert mock_preds.call_count == 5
    assert mock_insights.call_count == 5


@patch("ingestion.snowflake_sync.boto3.client")
def test_load_from_s3_success(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=b'{"key": "value"}'))
    }
    result = load_from_s3("test-bucket", "some/key.json")
    assert isinstance(result, dict)
    assert result == {"key": "value"}
