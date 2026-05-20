from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ingestion.fetch_stocks import fetch_stock_data, upload_to_s3


def _make_ohlcv_df():
    return pd.DataFrame(
        {
            "Open": [150.0],
            "High": [155.0],
            "Low": [149.0],
            "Close": [153.0],
            "Volume": [1_000_000],
        },
        index=pd.to_datetime(["2026-05-12"]),
    )


@patch("ingestion.fetch_stocks.yf.download")
def test_fetch_stock_data_success(mock_download):
    mock_download.return_value = _make_ohlcv_df()
    df = fetch_stock_data("AAPL")
    assert not df.empty


@patch("ingestion.fetch_stocks.yf.download")
def test_fetch_stock_data_invalid_ticker(mock_download):
    mock_download.return_value = pd.DataFrame()
    with pytest.raises(ValueError):
        fetch_stock_data("INVALID")


@patch("ingestion.fetch_stocks.boto3.client")
def test_s3_key_format(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    mock_s3.put_object.return_value = {}

    date = "2026/05/12"
    upload_to_s3({"price": 150.0}, "AAPL", "test-bucket", date)

    call_kwargs = mock_s3.put_object.call_args[1]
    assert call_kwargs["Key"] == "raw/stocks/2026/05/12/AAPL.json"


@patch("ingestion.fetch_stocks.boto3.client")
def test_upload_to_s3_success(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    mock_s3.put_object.return_value = {}

    result = upload_to_s3({"price": 150.0}, "AAPL", "test-bucket", "2026/05/12")
    assert result is True


@patch("ingestion.fetch_stocks.boto3.client")
def test_upload_to_s3_failure(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    mock_s3.put_object.side_effect = Exception("Connection error")

    result = upload_to_s3({"price": 150.0}, "AAPL", "test-bucket", "2026/05/12")
    assert result is False
