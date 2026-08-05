from ingestion.adaptive_model import (
    detect_concept_drift,
    select_best_model_for_regime,
    update_model_weights,
)


def test_update_model_weights_improves_accuracy():
    weights = {"gradient_boosting": 0.33, "ensemble": 0.34, "linear_regression": 0.33}
    updated = update_model_weights(weights, recent_accuracy=0.95, learning_rate=0.01)
    assert updated["gradient_boosting"] > weights["gradient_boosting"]


def test_detect_concept_drift_detected():
    recent_errors = [3.9, 4.1, 4.3, 4.5, 4.6]
    result = detect_concept_drift(recent_errors, baseline_error=3.0, threshold=0.2)
    assert result["drift_detected"] is True


def test_detect_concept_drift_not_detected():
    recent_errors = [3.0, 3.0, 3.0, 3.0, 3.0]
    result = detect_concept_drift(recent_errors, baseline_error=3.0, threshold=0.2)
    assert result["drift_detected"] is False


def test_select_best_model_trending():
    performance = {
        "gradient_boosting": {"accuracy": 0.82},
        "ensemble": {"accuracy": 0.79},
        "linear_regression": {"accuracy": 0.71},
    }
    result = select_best_model_for_regime("trending", performance)
    assert result == "gradient_boosting"


def test_select_best_model_volatile():
    performance = {
        "gradient_boosting": {"accuracy": 0.75},
        "ensemble": {"accuracy": 0.80},
        "linear_regression": {"accuracy": 0.70},
    }
    result = select_best_model_for_regime("volatile", performance)
    assert result == "ensemble"
