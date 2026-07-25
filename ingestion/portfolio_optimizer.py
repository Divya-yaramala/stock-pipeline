import datetime
import json
import logging
import math
import os  # noqa: F401
from typing import Any, Dict, List, Optional, Tuple  # noqa: F401

import boto3
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_efficient_frontier_points(
    returns: Dict[str, List[float]],
    num_portfolios: int = 100,
) -> List[Dict[str, Any]]:
    tickers = list(returns.keys())
    n = len(tickers)
    if n == 0:
        return []

    min_len = min(len(returns[t]) for t in tickers)
    ret_matrix = np.array([[float(r) for r in returns[t][:min_len]] for t in tickers])
    mean_returns = np.mean(ret_matrix, axis=1)
    cov_matrix = np.cov(ret_matrix)

    points: List[Dict[str, Any]] = []
    rng = np.random.default_rng(42)

    for _ in range(num_portfolios):
        raw = rng.random(n)
        w = raw / raw.sum()

        exp_return = float(np.dot(w, mean_returns)) * 252
        if n == 1:
            variance = float(w[0] ** 2 * float(np.var(ret_matrix[0])))
        else:
            variance = float(np.dot(w, np.dot(cov_matrix, w)))
        vol = float(math.sqrt(max(variance, 0.0))) * math.sqrt(252)
        sharpe = (exp_return - 0.05) / vol if vol > 0 else 0.0

        points.append(
            {
                "weights": {str(tickers[i]): round(float(w[i]), 4) for i in range(n)},
                "expected_return": round(exp_return, 6),
                "volatility": round(vol, 6),
                "sharpe": round(sharpe, 4),
            }
        )

    logger.info("Efficient frontier: %d portfolio points generated", len(points))
    return points


def find_max_sharpe_portfolio(
    frontier_points: List[Dict[str, Any]],
    risk_free_rate: float = 0.05,
) -> Dict[str, Any]:
    if not frontier_points:
        return {}
    best = max(frontier_points, key=lambda p: float(str(p.get("sharpe", 0.0))))
    logger.info("Max Sharpe portfolio: sharpe=%.4f", float(str(best.get("sharpe", 0.0))))
    return best


def find_min_volatility_portfolio(
    frontier_points: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not frontier_points:
        return {}
    best = min(frontier_points, key=lambda p: float(str(p.get("volatility", 9999.0))))
    logger.info("Min volatility portfolio: vol=%.4f", float(str(best.get("volatility", 0.0))))
    return best


def calculate_rebalancing_trades(
    current_weights: Dict[str, float],
    target_weights: Dict[str, float],
    portfolio_value: float,
) -> List[Dict[str, Any]]:
    trades: List[Dict[str, Any]] = []
    all_tickers = set(list(current_weights.keys()) + list(target_weights.keys()))
    pv = float(str(portfolio_value))

    for ticker in sorted(all_tickers):
        cur = float(str(current_weights.get(ticker, 0.0)))
        tgt = float(str(target_weights.get(ticker, 0.0)))
        diff = tgt - cur
        amount = round(abs(diff) * pv, 2)
        if abs(diff) < 0.001:
            continue
        action = "BUY" if diff > 0 else "SELL"
        trades.append({"ticker": str(ticker), "action": action, "amount": amount})

    logger.info("Rebalancing: %d trades calculated", len(trades))
    return trades


def run_portfolio_optimization(
    ticker_returns: Dict[str, List[float]],
    current_weights: Dict[str, float],
    portfolio_value: float,
    bucket: str,
) -> Dict[str, Any]:
    frontier_points = calculate_efficient_frontier_points(ticker_returns)
    max_sharpe = find_max_sharpe_portfolio(frontier_points)
    min_vol = find_min_volatility_portfolio(frontier_points)

    target_weights = dict(max_sharpe.get("weights", {}))
    trades = calculate_rebalancing_trades(current_weights, target_weights, portfolio_value)

    result: Dict[str, Any] = {
        "frontier_point_count": len(frontier_points),
        "max_sharpe": max_sharpe,
        "min_volatility": min_vol,
        "rebalancing_trades": trades,
        "current_weights": current_weights,
        "optimized_at": datetime.datetime.utcnow().isoformat(),
    }

    now = datetime.datetime.utcnow()
    s3_key = "processed/portfolio_optimization/{}/{}/{}/result.json".format(
        now.strftime("%Y"),
        now.strftime("%m"),
        now.strftime("%d"),
    )

    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=json.dumps(result),
            ContentType="application/json",
        )
        logger.info("Saved portfolio optimization to s3://%s/%s", bucket, s3_key)
    except Exception as e:
        logger.warning("S3 upload skipped: %s", str(e))

    logger.info("Portfolio Optimization Complete")
    return result


if __name__ == "__main__":
    pass
