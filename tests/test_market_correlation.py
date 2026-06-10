import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from ingestion.market_correlation import (
    calculate_beta,
    calculate_correlation_matrix,
    find_highly_correlated,
    load_price_series,
)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def _make_price_df(n=30):
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    data = {t: np.random.uniform(100, 300, n) for t in TICKERS}
    return pd.DataFrame(data, index=dates)


def test_correlation_matrix_shape():
    df = _make_price_df()
    corr = calculate_correlation_matrix(df)
    assert corr.shape == (5, 5)
    assert list(corr.columns) == TICKERS


def test_correlation_matrix_diagonal_is_one():
    df = _make_price_df()
    corr = calculate_correlation_matrix(df)
    for ticker in TICKERS:
        assert abs(corr.loc[ticker, ticker] - 1.0) < 1e-9


def test_find_highly_correlated_pairs():
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    base = np.linspace(100, 200, 30)
    data = {
        "AAPL": base,
        "MSFT": base * 1.01,
        "GOOGL": base[::-1],
        "AMZN": np.random.uniform(100, 300, 30),
        "TSLA": np.random.uniform(50, 400, 30),
    }
    df = pd.DataFrame(data, index=dates)
    corr = df.corr()
    pairs = find_highly_correlated(corr, threshold=0.8)
    assert isinstance(pairs, list)
    for p in pairs:
        assert "ticker1" in p
        assert "ticker2" in p
        assert abs(p["correlation"]) >= 0.8
    tickers_in_pairs = {p["ticker1"] for p in pairs} | {p["ticker2"] for p in pairs}
    assert "AAPL" in tickers_in_pairs or "MSFT" in tickers_in_pairs


def test_calculate_beta_positive():
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    market = np.linspace(100, 150, 30)
    stock = market * 1.5 + np.random.normal(0, 0.5, 30)
    df = pd.DataFrame({"AAPL": stock, "MSFT": market}, index=dates)
    beta = calculate_beta("AAPL", "MSFT", df)
    assert beta > 0


def test_load_price_series_returns_dataframe():
    mock_s3 = MagicMock()
    record = json.dumps([{"close": 150.0}]).encode("utf-8")
    mock_s3.get_object.return_value = {"Body": BytesIO(record)}

    with patch("ingestion.market_correlation.boto3.client", return_value=mock_s3):
        df = load_price_series(["AAPL", "MSFT"], "test-bucket", days=5)

    assert isinstance(df, pd.DataFrame)
    assert "AAPL" in df.columns
    assert "MSFT" in df.columns
