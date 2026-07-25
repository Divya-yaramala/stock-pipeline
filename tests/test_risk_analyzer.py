import pytest  # noqa: F401

from ingestion.risk_analyzer import (
    calculate_cvar,
    calculate_portfolio_var,
    calculate_risk_metrics,
    calculate_var,
    classify_risk_level,
)


def test_calculate_var_negative():
    returns = [-0.03, -0.02, -0.01, 0.01, 0.02, 0.03, -0.04, 0.005, -0.015, 0.025]
    var = calculate_var(returns, confidence_level=0.95)
    assert isinstance(var, float)
    assert var < 0


def test_calculate_cvar_less_than_var():
    returns = [-0.05, -0.04, -0.03, -0.02, -0.01, 0.01, 0.02, 0.03, 0.04, 0.05]
    var = calculate_var(returns, confidence_level=0.95)
    cvar = calculate_cvar(returns, confidence_level=0.95)
    assert cvar <= var


def test_calculate_risk_metrics_structure():
    import numpy as np

    rng = np.random.default_rng(0)
    returns = list(rng.normal(0.001, 0.02, 30))
    result = calculate_risk_metrics(returns, "AAPL")
    assert "annualized_volatility" in result
    assert "var_95" in result
    assert "cvar_95" in result
    assert "max_drawdown" in result


def test_classify_risk_level_valid():
    metrics = {"annualized_volatility": 0.25, "var_95": -0.03}
    level = classify_risk_level(metrics)
    assert level in ("LOW", "MEDIUM", "HIGH", "VERY_HIGH")


def test_calculate_portfolio_var_structure():
    import numpy as np

    rng = np.random.default_rng(1)
    ticker_returns = {
        "AAPL": list(rng.normal(0.001, 0.02, 60)),
        "MSFT": list(rng.normal(0.0008, 0.018, 60)),
        "GOOGL": list(rng.normal(0.0012, 0.022, 60)),
    }
    weights = {"AAPL": 1 / 3, "MSFT": 1 / 3, "GOOGL": 1 / 3}
    result = calculate_portfolio_var(weights, ticker_returns)
    assert "portfolio_var" in result
    assert "portfolio_cvar" in result
