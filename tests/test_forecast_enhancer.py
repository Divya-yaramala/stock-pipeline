import pytest  # noqa: F401

from ingestion.forecast_enhancer import (
    add_confidence_intervals,
    blend_forecasts,
    calculate_forecast_accuracy,
    generate_scenario_forecasts,
)


def test_add_confidence_intervals_structure():
    predictions = [185.0, 186.0, 187.0, 188.0, 189.0]
    result = add_confidence_intervals(predictions, historical_volatility=2.0)
    assert isinstance(result, list)
    assert len(result) == 5
    assert all("lower" in d and "upper" in d for d in result)


def test_blend_forecasts_weighted():
    prophet = [100.0]
    ensemble = [110.0]
    result = blend_forecasts(prophet, ensemble, prophet_weight=0.6)
    assert abs(result[0] - 104.0) < 0.01


def test_calculate_forecast_accuracy_structure():
    predictions = [185.0, 186.0, 184.0, 187.0, 185.5]
    actuals = [186.0, 185.5, 184.5, 188.0, 185.0]
    result = calculate_forecast_accuracy(predictions, actuals)
    assert "MAE" in result
    assert "RMSE" in result
    assert "MAPE" in result
    assert "directional_accuracy" in result


def test_generate_scenario_forecasts_structure():
    result = generate_scenario_forecasts(base_prediction=185.0, volatility=2.0)
    assert result["bull"] > result["base"]
    assert result["base"] > result["bear"]
    assert result["base"] == 185.0


def test_add_confidence_intervals_upper_above_lower():
    predictions = [200.0, 201.0, 202.0]
    result = add_confidence_intervals(predictions, historical_volatility=1.5)
    assert all(d["upper"] > d["lower"] for d in result)
