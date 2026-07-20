from ingestion.streaming_analytics import (
    calculate_window_stats,
    create_sliding_window,
    detect_streaming_anomaly,
    process_price_stream,
    update_window,
)


def test_create_sliding_window_size():
    window = create_sliding_window(window_size=10)
    assert window.maxlen == 10


def test_update_window_drops_oldest():
    window = create_sliding_window(window_size=3)
    for v in [1.0, 2.0, 3.0, 4.0]:
        update_window(window, v)
    assert list(window) == [2.0, 3.0, 4.0]
    assert 1.0 not in window


def test_calculate_window_stats_structure():
    window = create_sliding_window(window_size=5)
    for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
        update_window(window, v)
    stats = calculate_window_stats(window)
    assert "mean" in stats
    assert "std" in stats
    assert "min" in stats
    assert "max" in stats
    assert "latest" in stats
    assert "change_pct" in stats


def test_detect_streaming_anomaly_spike():
    window = create_sliding_window(window_size=20)
    for v in [100.0] * 19:
        update_window(window, v)
    update_window(window, 500.0)
    result = detect_streaming_anomaly(window, z_score_threshold=2.5)
    assert result["is_anomaly"] is True
    assert result["direction"] == "spike"


def test_process_price_stream_structure():
    prices = [float(100 + i) for i in range(30)]
    result = process_price_stream("TEST", prices, window_size=10)
    assert "processed" in result
    assert "anomalies" in result
    assert result["processed"] == 30
