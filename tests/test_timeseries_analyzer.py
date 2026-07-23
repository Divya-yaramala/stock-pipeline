import pytest  # noqa: F401

from ingestion.timeseries_analyzer import (
    calculate_autocorrelation,
    calculate_drawdown_series,
    calculate_volatility_regime,
    detect_trend,
)


def test_calculate_autocorrelation_structure():
    prices = [float(180 + i * 0.5) for i in range(30)]
    result = calculate_autocorrelation(prices)
    assert isinstance(result, dict)
    assert all(isinstance(k, int) for k in result.keys())
    assert len(result) == 10


def test_detect_trend_uptrend():
    prices = [float(100 + i * 2) for i in range(30)]
    result = detect_trend(prices)
    assert result["trend"] == "uptrend"


def test_detect_trend_downtrend():
    prices = [float(200 - i * 2) for i in range(30)]
    result = detect_trend(prices)
    assert result["trend"] == "downtrend"


def test_calculate_volatility_regime_structure():
    prices = [float(180 + i * 0.1) for i in range(30)]
    result = calculate_volatility_regime(prices)
    assert "regime" in result
    assert result["regime"] in ("low", "medium", "high")
    assert "current_vol" in result
    assert "avg_vol" in result


def test_calculate_drawdown_series_structure():
    prices = [100.0, 110.0, 105.0, 95.0, 108.0, 102.0]
    result = calculate_drawdown_series(prices)
    assert "max_drawdown" in result
    assert "current_drawdown" in result
    assert "drawdown_series" in result
    assert result["max_drawdown"] <= 0.0
