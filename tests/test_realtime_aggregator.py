from ingestion.realtime_aggregator import (
    aggregate_ohlcv,
    calculate_volume_profile,
    calculate_vwap,
    detect_momentum,
)


def test_aggregate_ohlcv_structure():
    prices = [
        {"price": 185.0, "volume": 1000, "timestamp": "2026-07-18T09:30:00"},
        {"price": 186.0, "volume": 1500, "timestamp": "2026-07-18T09:32:00"},
        {"price": 184.5, "volume": 800, "timestamp": "2026-07-18T09:35:00"},
        {"price": 187.0, "volume": 1200, "timestamp": "2026-07-18T09:37:00"},
    ]
    bars = aggregate_ohlcv(prices, window_minutes=5)
    assert isinstance(bars, list)
    assert len(bars) > 0
    bar = bars[0]
    assert "open" in bar
    assert "high" in bar
    assert "low" in bar
    assert "close" in bar


def test_calculate_vwap_correct():
    prices = [
        {"price": 100.0, "volume": 1000},
        {"price": 200.0, "volume": 1000},
    ]
    vwap = calculate_vwap(prices)
    assert abs(vwap - 150.0) < 0.01


def test_calculate_volume_profile_structure():
    prices = [
        {"price": 185.0, "volume": 1000},
        {"price": 186.0, "volume": 2000},
        {"price": 187.0, "volume": 500},
        {"price": 188.0, "volume": 1500},
        {"price": 185.5, "volume": 800},
    ]
    profile = calculate_volume_profile(prices, num_buckets=5)
    assert "buckets" in profile
    assert "poc" in profile
    assert isinstance(profile["buckets"], list)


def test_detect_momentum_bullish():
    # Upward-trending prices so short MA > long MA
    prices = list(range(1, 22))  # 1..21, short last 5 avg=19, long last 20 avg=11.5
    result = detect_momentum(prices, short_period=5, long_period=20)
    assert result["momentum"] == "bullish"
    assert result["short_ma"] > result["long_ma"]


def test_detect_momentum_bearish():
    # Downward-trending prices so short MA < long MA
    prices = list(range(21, 0, -1))  # 21..1, short last 5 avg=3, long last 20 avg=11.5
    result = detect_momentum(prices, short_period=5, long_period=20)
    assert result["momentum"] == "bearish"
    assert result["short_ma"] < result["long_ma"]
