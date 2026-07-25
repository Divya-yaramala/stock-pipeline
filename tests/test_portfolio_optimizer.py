from unittest.mock import MagicMock, patch

import pytest  # noqa: F401

from ingestion.portfolio_optimizer import (
    calculate_efficient_frontier_points,
    calculate_rebalancing_trades,
    find_max_sharpe_portfolio,
    find_min_volatility_portfolio,
    run_portfolio_optimization,
)


def test_calculate_efficient_frontier_points_count():
    import numpy as np

    rng = np.random.default_rng(0)
    returns = {
        "AAPL": list(rng.normal(0.001, 0.02, 60)),
        "MSFT": list(rng.normal(0.0008, 0.018, 60)),
    }
    points = calculate_efficient_frontier_points(returns, num_portfolios=10)
    assert len(points) == 10


def test_find_max_sharpe_portfolio_structure():
    frontier = [
        {
            "weights": {"AAPL": 0.6, "MSFT": 0.4},
            "expected_return": 0.12,
            "volatility": 0.18,
            "sharpe": 0.39,
        },
        {
            "weights": {"AAPL": 0.3, "MSFT": 0.7},
            "expected_return": 0.10,
            "volatility": 0.20,
            "sharpe": 0.25,
        },
    ]
    result = find_max_sharpe_portfolio(frontier)
    assert "sharpe" in result
    assert result["sharpe"] == 0.39


def test_find_min_volatility_portfolio_structure():
    frontier = [
        {
            "weights": {"AAPL": 0.6, "MSFT": 0.4},
            "expected_return": 0.12,
            "volatility": 0.18,
            "sharpe": 0.39,
        },
        {
            "weights": {"AAPL": 0.3, "MSFT": 0.7},
            "expected_return": 0.10,
            "volatility": 0.15,
            "sharpe": 0.25,
        },
    ]
    result = find_min_volatility_portfolio(frontier)
    assert "volatility" in result
    assert result["volatility"] == 0.15


def test_calculate_rebalancing_trades_buy_sell():
    current = {"AAPL": 0.3, "MSFT": 0.7}
    target = {"AAPL": 0.5, "MSFT": 0.5}
    trades = calculate_rebalancing_trades(current, target, portfolio_value=10000)
    actions = {t["ticker"]: t["action"] for t in trades}
    assert actions["AAPL"] == "BUY"
    assert actions["MSFT"] == "SELL"


def test_run_portfolio_optimization_structure():
    import numpy as np

    rng = np.random.default_rng(2)
    ticker_returns = {
        "AAPL": list(rng.normal(0.001, 0.02, 60)),
        "MSFT": list(rng.normal(0.0008, 0.018, 60)),
    }
    current_weights = {"AAPL": 0.5, "MSFT": 0.5}

    with patch("ingestion.portfolio_optimizer.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        result = run_portfolio_optimization(ticker_returns, current_weights, 10000, "test-bucket")

    assert "max_sharpe" in result
    assert "min_volatility" in result
    assert "rebalancing_trades" in result
