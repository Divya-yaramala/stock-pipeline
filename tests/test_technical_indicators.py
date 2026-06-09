from ingestion.technical_indicators import (
    calculate_bollinger_bands,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
)


def test_calculate_sma_correct():
    prices = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = calculate_sma(prices, window=3)
    assert result[2] == 2.0
    assert result[4] == 4.0


def test_calculate_rsi_range():
    prices = [float(i) for i in range(1, 30)]
    result = calculate_rsi(prices, period=14)
    valid = [v for v in result if v is not None]
    assert len(valid) > 0
    assert all(0 <= v <= 100 for v in valid)


def test_calculate_bollinger_bands_structure():
    prices = [float(i) for i in range(1, 31)]
    result = calculate_bollinger_bands(prices, window=20)
    assert "upper_band" in result
    assert "middle_band" in result
    assert "lower_band" in result


def test_bollinger_upper_above_lower():
    prices = [float(i) for i in range(1, 31)]
    result = calculate_bollinger_bands(prices, window=20)
    for u, l in zip(result["upper_band"], result["lower_band"]):
        if u is not None and l is not None:
            assert u > l


def test_calculate_macd_structure():
    prices = [float(i) + 0.1 * (i % 3) for i in range(1, 60)]
    result = calculate_macd(prices)
    assert "macd_line" in result
    assert "signal_line" in result
    assert "histogram" in result
