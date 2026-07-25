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


def calculate_var(
    returns: List[float],
    confidence_level: float = 0.95,
) -> float:
    if not returns:
        return 0.0
    sorted_returns = sorted(returns)
    index = int((1.0 - confidence_level) * len(sorted_returns))
    var = float(sorted_returns[max(0, index)])
    logger.info("VaR %.0f%%: %.4f", confidence_level * 100, var)
    return var


def calculate_cvar(
    returns: List[float],
    confidence_level: float = 0.95,
) -> float:
    if not returns:
        return 0.0
    var = calculate_var(returns, confidence_level)
    tail = [float(r) for r in returns if float(r) <= var]
    cvar = float(np.mean(tail)) if tail else var
    logger.info("CVaR %.0f%%: %.4f", confidence_level * 100, cvar)
    return cvar


def calculate_portfolio_var(
    portfolio_weights: Dict[str, float],
    ticker_returns: Dict[str, List[float]],
    confidence_level: float = 0.95,
) -> Dict[str, float]:
    tickers = list(portfolio_weights.keys())
    min_len = min(len(ticker_returns.get(t, [])) for t in tickers) if tickers else 0

    portfolio_returns: List[float] = []
    for i in range(min_len):
        pr = sum(
            float(str(portfolio_weights[t])) * float(str(ticker_returns[t][i]))
            for t in tickers
            if t in ticker_returns
        )
        portfolio_returns.append(pr)

    p_var = calculate_var(portfolio_returns, confidence_level)
    p_cvar = calculate_cvar(portfolio_returns, confidence_level)

    result: Dict[str, float] = {
        "portfolio_var": round(p_var, 6),
        "portfolio_cvar": round(p_cvar, 6),
    }
    logger.info("Portfolio VaR=%.4f CVaR=%.4f", p_var, p_cvar)
    return result


def calculate_risk_metrics(returns: List[float], ticker: str) -> Dict[str, Any]:
    if not returns:
        return {}

    n = len(returns)
    mean = float(np.mean(returns))
    std = float(np.std(returns))
    annualized_volatility = std * math.sqrt(252)

    var_95 = calculate_var(returns, 0.95)
    cvar_95 = calculate_cvar(returns, 0.95)

    if std > 0:
        skewness = float(np.mean([(r - mean) ** 3 for r in returns]) / (std**3))
        kurtosis = float(np.mean([(r - mean) ** 4 for r in returns]) / (std**4)) - 3.0
    else:
        skewness = 0.0
        kurtosis = 0.0

    peak = float(returns[0])
    max_dd = 0.0
    for r in returns:
        val = float(r)
        if val > peak:
            peak = val
        dd = (val - peak) / peak if peak != 0 else 0.0
        if dd < max_dd:
            max_dd = dd

    result: Dict[str, Any] = {
        "ticker": ticker,
        "annualized_volatility": round(annualized_volatility, 6),
        "var_95": round(var_95, 6),
        "cvar_95": round(cvar_95, 6),
        "skewness": round(skewness, 4),
        "kurtosis": round(kurtosis, 4),
        "max_drawdown": round(max_dd, 6),
        "sample_size": n,
    }
    logger.info(
        "Risk metrics for %s — vol=%.4f var95=%.4f cvar95=%.4f",
        ticker,
        annualized_volatility,
        var_95,
        cvar_95,
    )
    return result


def classify_risk_level(metrics: Dict[str, Any]) -> str:
    vol = float(str(metrics.get("annualized_volatility", 0.0)))
    var = abs(float(str(metrics.get("var_95", 0.0))))

    if vol < 0.15 and var < 0.02:
        level = "LOW"
    elif vol < 0.30 and var < 0.04:
        level = "MEDIUM"
    elif vol < 0.50 and var < 0.07:
        level = "HIGH"
    else:
        level = "VERY_HIGH"

    logger.info("Risk classification: %s (vol=%.4f, var=%.4f)", level, vol, var)
    return level


def run_risk_analysis(
    ticker_returns: Dict[str, List[float]],
    portfolio_weights: Dict[str, float],
    bucket: str,
) -> Dict[str, Any]:
    ticker_risk: Dict[str, Any] = {}
    for ticker, returns in ticker_returns.items():
        metrics = calculate_risk_metrics(returns, str(ticker))
        metrics["risk_level"] = classify_risk_level(metrics)
        ticker_risk[str(ticker)] = metrics

    portfolio = calculate_portfolio_var(portfolio_weights, ticker_returns)

    result: Dict[str, Any] = {
        "ticker_risk": ticker_risk,
        "portfolio": portfolio,
        "portfolio_weights": portfolio_weights,
        "analyzed_at": datetime.datetime.utcnow().isoformat(),
    }

    now = datetime.datetime.utcnow()
    s3_key = "processed/risk_analysis/{}/{}/{}/analysis.json".format(
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
        logger.info("Saved risk analysis to s3://%s/%s", bucket, s3_key)
    except Exception as e:
        logger.warning("S3 upload skipped: %s", str(e))

    logger.info("Risk Analysis Complete")
    return result


if __name__ == "__main__":
    pass
