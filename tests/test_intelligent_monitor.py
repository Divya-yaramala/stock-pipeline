from ingestion.intelligent_monitor import (
    calculate_health_fingerprint,
    correlate_metrics,
    detect_metric_anomaly,
    generate_root_cause_hypothesis,
)


def test_correlate_metrics_structure():
    metrics = {
        "quality_score": [90.0, 88.0, 86.0, 84.0, 82.0],
        "anomaly_rate": [0.1, 0.2, 0.3, 0.4, 0.5],
    }
    result = correlate_metrics(metrics)
    assert isinstance(result, dict)
    for key in result:
        assert isinstance(key, str)


def test_detect_metric_anomaly_found():
    values = [90.0, 91.0, 90.5, 89.8, 90.2, 90.1, 90.3, 140.0]
    result = detect_metric_anomaly("quality_score", values, z_threshold=2.5)
    assert result["anomaly_detected"] is True


def test_detect_metric_anomaly_not_found():
    values = [90.0, 91.0, 90.5, 89.8, 90.2, 90.1, 90.3, 90.0]
    result = detect_metric_anomaly("quality_score", values, z_threshold=2.5)
    assert result["anomaly_detected"] is False


def test_generate_root_cause_hypothesis_returns_list():
    correlations = {
        "quality_score_vs_anomaly_rate": 0.85,
        "quality_score_vs_pipeline_duration": 0.72,
    }
    result = generate_root_cause_hypothesis("quality_score", correlations)
    assert isinstance(result, list)
    assert len(result) > 0
    for h in result:
        assert isinstance(h, str)


def test_calculate_health_fingerprint_consistent():
    metrics = {"quality_score": 90.0, "anomaly_rate": 0.1, "pipeline_duration": 6.5}
    fp1 = calculate_health_fingerprint(metrics)
    fp2 = calculate_health_fingerprint(metrics)
    assert isinstance(fp1, str)
    assert fp1 == fp2
