from ingestion.pipeline_optimizer import (
    calculate_pipeline_efficiency,
    generate_optimization_recommendations,
    identify_bottlenecks,
    profile_pipeline_step,
)


def test_profile_pipeline_step_structure():
    result = profile_pipeline_step("test_step", lambda: 42)
    assert "duration_seconds" in result
    assert "step" in result
    assert "success" in result
    assert result["success"] is True


def test_identify_bottlenecks_finds_slow():
    profiles = [
        {"step": "slow_step", "duration_seconds": 15.0},
        {"step": "fast_step", "duration_seconds": 2.0},
    ]
    bottlenecks = identify_bottlenecks(profiles, threshold_seconds=10.0)
    assert len(bottlenecks) == 1
    assert bottlenecks[0]["step"] == "slow_step"


def test_identify_bottlenecks_none():
    profiles = [
        {"step": "step_a", "duration_seconds": 3.0},
        {"step": "step_b", "duration_seconds": 5.0},
    ]
    bottlenecks = identify_bottlenecks(profiles, threshold_seconds=10.0)
    assert bottlenecks == []


def test_calculate_pipeline_efficiency_structure():
    profiles = [
        {"step": "step_a", "duration_seconds": 5.0},
        {"step": "step_b", "duration_seconds": 10.0},
        {"step": "step_c", "duration_seconds": 2.0},
    ]
    result = calculate_pipeline_efficiency(profiles)
    assert "total_seconds" in result
    assert "slowest_step" in result
    assert "fastest_step" in result
    assert "efficiency_score" in result
    assert result["total_seconds"] == 17.0


def test_generate_optimization_recommendations_returns_list():
    bottlenecks = [
        {"step": "fetch_stocks", "duration_seconds": 15.2},
        {"step": "anomaly_detect", "duration_seconds": 12.5},
    ]
    recs = generate_optimization_recommendations(bottlenecks)
    assert isinstance(recs, list)
    assert len(recs) == 2
    assert all(isinstance(r, str) for r in recs)
    assert "fetch_stocks" in recs[0]
