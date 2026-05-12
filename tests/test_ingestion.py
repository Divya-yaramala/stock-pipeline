from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ingestion.fetch_stock_prices import fetch_stock_data


def test_fetch_stock_data_returns_dataframe():
    mock_df = pd.DataFrame({
        "Date": ["2024-01-02"],
        "Open": [185.0],
        "High": [188.0],
        "Low": [184.0],
        "Close": [187.0],
        "Volume": [50000000],
    })
    mock_df.set_index("Date", inplace=True)

    with patch("ingestion.fetch_stock_prices.yf.download", return_value=mock_df):
        result = fetch_stock_data(["AAPL"], "2024-01-02", "2024-01-03")

    assert isinstance(result, pd.DataFrame)
    assert "ticker" in result.columns
    assert result["ticker"].iloc[0] == "AAPL"


def test_fetch_stock_data_multiple_tickers():
    arrays = pd.MultiIndex.from_tuples(
        [("Close", "AAPL"), ("Close", "MSFT"), ("Open", "AAPL"), ("Open", "MSFT")],
        names=["Price", "Ticker"],
    )
    mock_df = pd.DataFrame(
        [[187.0, 375.0, 185.0, 373.0]],
        index=pd.to_datetime(["2024-01-02"]),
        columns=arrays,
    )
    mock_df.index.name = "Date"

    with patch("ingestion.fetch_stock_prices.yf.download", return_value=mock_df):
        result = fetch_stock_data(["AAPL", "MSFT"], "2024-01-02", "2024-01-03")

    assert set(result["ticker"].unique()) == {"AAPL", "MSFT"}
