from typing import Any, Dict, List

from ingestion.drift_detector import (
    calculate_distribution_stats,
    calculate_psi,
    should_trigger_retraining,
)


def test_calculate_psi_no_drift():
    values: List[float] = [float(i) for i in range(1, 101)]
    psi = calculate_psi(values, values)
    assert psi < 0.1


def test_calculate_psi_high_drift():
    baseline: List[float] = [1.0] * 100
    current: List[float] = [100.0] * 100
    psi = calculate_psi(baseline, current)
    assert psi > 0.25


def test_calculate_distribution_stats_structure():
    values: List[float] = [1.0, 2.0, 3.0, 4.0, 5.0]
    stats = calculate_distribution_stats(values)
    assert isinstance(stats, dict)
    assert "mean" in stats
    assert "std" in stats


def test_should_trigger_retraining_significant():
    drift_results: List[Dict[str, Any]] = [
        {
            "feature": "close",
            "psi_score": 0.3,
            "drift_detected": True,
            "severity": "significant",
        }
    ]
    result = should_trigger_retraining(drift_results)
    assert result is True


def test_should_trigger_retraining_none():
    drift_results: List[Dict[str, Any]] = [
        {"feature": "close", "psi_score": 0.05, "drift_detected": False, "severity": "none"},
        {"feature": "volume", "psi_score": 0.04, "drift_detected": False, "severity": "none"},
    ]
    result = should_trigger_retraining(drift_results)
    assert result is False
