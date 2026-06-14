import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from ingestion.data_catalog import (
    get_dataset_lineage,
    register_dataset,
    search_catalog,
    update_dataset_stats,
)

SAMPLE_SCHEMA = {"ticker": "VARCHAR(10)", "trade_date": "DATE", "close_price": "NUMERIC(12,4)"}

SAMPLE_ENTRY = {
    "dataset_id": "abc123",
    "dataset_name": "stock_prices_raw",
    "description": "Raw OHLCV data",
    "schema": SAMPLE_SCHEMA,
    "source": "yfinance",
    "owner": "data-engineering",
    "registered_at": "2026-06-14T00:00:00+00:00",
    "tags": [],
    "status": "active",
}


def test_register_dataset_success():
    mock_s3 = MagicMock()
    with patch("ingestion.data_catalog.boto3.client", return_value=mock_s3):
        dataset_id = register_dataset(
            dataset_name="stock_prices_raw",
            description="Raw OHLCV data",
            schema=SAMPLE_SCHEMA,
            source="yfinance",
            owner="data-engineering",
            bucket="test-bucket",
        )
    assert isinstance(dataset_id, str)
    assert len(dataset_id) == 32
    mock_s3.put_object.assert_called_once()


def test_register_dataset_correct_path():
    mock_s3 = MagicMock()
    with patch("ingestion.data_catalog.boto3.client", return_value=mock_s3):
        register_dataset(
            dataset_name="stock_prices_raw",
            description="Raw OHLCV data",
            schema=SAMPLE_SCHEMA,
            source="yfinance",
            owner="data-engineering",
            bucket="test-bucket",
        )
    call_kwargs = mock_s3.put_object.call_args.kwargs
    assert "catalog/datasets/" in call_kwargs["Key"]
    assert "stock_prices_raw" in call_kwargs["Key"]


def test_search_catalog_found():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "catalog/datasets/stock_prices_raw/metadata.json"}]
    }
    mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(SAMPLE_ENTRY).encode())}
    with patch("ingestion.data_catalog.boto3.client", return_value=mock_s3):
        results = search_catalog("raw", "test-bucket")
    assert len(results) >= 1
    assert results[0]["dataset_name"] == "stock_prices_raw"


def test_update_dataset_stats_success():
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(SAMPLE_ENTRY).encode())}
    with patch("ingestion.data_catalog.boto3.client", return_value=mock_s3):
        result = update_dataset_stats(
            dataset_name="stock_prices_raw",
            row_count=500,
            last_updated="2026-06-14",
            bucket="test-bucket",
        )
    assert result is True
    mock_s3.put_object.assert_called_once()
    saved = json.loads(mock_s3.put_object.call_args.kwargs["Body"].decode())
    assert saved["row_count"] == 500


def test_get_dataset_lineage_structure():
    mock_s3 = MagicMock()
    lineage = {"upstream": ["yahoo_finance_api"], "downstream": ["stock_anomalies"]}
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "lineage/stock_prices_raw/2026-06-14.json"}]
    }
    mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(lineage).encode())}
    with patch("ingestion.data_catalog.boto3.client", return_value=mock_s3):
        result = get_dataset_lineage("stock_prices_raw", "test-bucket")
    assert "upstream" in result
    assert "downstream" in result
    assert isinstance(result["upstream"], list)
    assert isinstance(result["downstream"], list)
