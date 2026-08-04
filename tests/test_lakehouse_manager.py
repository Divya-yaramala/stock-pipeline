from unittest.mock import MagicMock, patch

from ingestion.lakehouse_manager import (
    run_lakehouse_pipeline,
    write_to_bronze,
    write_to_gold,
    write_to_silver,
)


def test_write_to_bronze_returns_id():
    data = {"ticker": "AAPL", "close_price": 188.0}
    with patch("ingestion.lakehouse_manager.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        result = write_to_bronze(data, "AAPL", "yahoo_finance", "test-bucket")
    assert isinstance(result, str)
    assert len(result) > 0
    mock_s3.put_object.assert_called_once()


def test_write_to_silver_passes_validation():
    data = {"ticker": "AAPL", "close_price": 188.0}
    with patch("ingestion.lakehouse_manager.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        result = write_to_silver(data, "AAPL", 90.0, "test-bucket")
    assert isinstance(result, str)
    assert len(result) > 0
    mock_s3.put_object.assert_called_once()


def test_write_to_silver_fails_validation():
    data = {"ticker": "AAPL", "close_price": 188.0}
    result = write_to_silver(data, "AAPL", 70.0, "test-bucket")
    assert result == ""


def test_write_to_gold_returns_id():
    aggregation = {"avg_price": 188.0, "total_volume": 1000000}
    with patch("ingestion.lakehouse_manager.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        result = write_to_gold(aggregation, "AAPL", "daily_summary", "test-bucket")
    assert isinstance(result, str)
    assert len(result) > 0
    mock_s3.put_object.assert_called_once()


def test_run_lakehouse_pipeline_structure():
    raw_data = {
        "ticker": "AAPL",
        "trade_date": "2026-07-31",
        "open_price": 185.0,
        "high_price": 190.0,
        "low_price": 183.0,
        "close_price": 188.0,
        "volume": 1000000,
    }
    with patch("ingestion.lakehouse_manager.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        result = run_lakehouse_pipeline("AAPL", raw_data, "test-bucket")
    assert "bronze_id" in result
    assert "silver_id" in result
    assert "gold_id" in result
    assert "validation_score" in result
