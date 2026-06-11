import numpy as np
import pandas as pd

from ingestion.feature_engineer import (
    add_momentum_features,
    add_price_features,
    add_volume_features,
)


def _sample_ohlcv(n: int = 30) -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    base = np.linspace(100, 150, n)
    return pd.DataFrame(
        {
            "date": dates,
            "open": base,
            "high": base + np.random.uniform(1, 5, n),
            "low": base - np.random.uniform(1, 5, n),
            "close": base + np.random.uniform(-2, 4, n),
            "volume": np.random.uniform(1_000_000, 5_000_000, n),
        }
    )


def test_add_price_features_columns():
    df = _sample_ohlcv()
    result = add_price_features(df)
    for col in ["daily_return", "high_low_range", "price_position"]:
        assert col in result.columns, f"Missing column: {col}"


def test_add_volume_features_columns():
    df = _sample_ohlcv()
    result = add_volume_features(df)
    for col in ["volume_sma_20", "volume_ratio", "high_volume"]:
        assert col in result.columns, f"Missing column: {col}"


def test_add_momentum_features_columns():
    df = _sample_ohlcv()
    result = add_momentum_features(df)
    for col in ["roc_5", "roc_10", "momentum_signal"]:
        assert col in result.columns, f"Missing column: {col}"


def test_daily_return_calculation():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=1),
            "open": [100.0],
            "high": [115.0],
            "low": [95.0],
            "close": [110.0],
            "volume": [1_000_000.0],
        }
    )
    result = add_price_features(df)
    assert abs(result["daily_return"].iloc[0] - 10.0) < 1e-6


def test_price_position_range():
    np.random.seed(7)
    n = 20
    low = np.random.uniform(90, 100, n)
    high = low + np.random.uniform(5, 15, n)
    close = low + np.random.uniform(0, 1, n) * (high - low)
    df = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=n),
            "open": low + np.random.uniform(0, 1, n) * (high - low),
            "high": high,
            "low": low,
            "close": close,
            "volume": np.ones(n) * 1_000_000,
        }
    )
    result = add_price_features(df)
    valid = result["price_position"].dropna()
    assert (valid >= 0).all(), "price_position should be >= 0"
    assert (valid <= 1).all(), "price_position should be <= 1"
