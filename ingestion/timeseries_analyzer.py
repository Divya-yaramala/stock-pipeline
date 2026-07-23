import numpy as np
import pandas as pd
import json
import os
import logging
import datetime
import boto3
from typing import Optional, Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_autocorrelation(
    values: List[float], max_lag: int = 10
) -> Dict[int, float]:
    n = len(values)
    mean = float(np.mean(values))
    variance = float(np.var(values))
    result: Dict[int, float] = {}
    if variance == 0:
        return {lag: 0.0 for lag in range(1, max_lag + 1)}
    for lag in range(1, max_lag + 1):
        if lag >= n:
            result[lag] = 0.0
            continue
        cov = sum(
            (float(values[i]) - mean) * (float(values[i - lag]) - mean)
            for i in range(lag, n)
        ) / float(n)
        result[lag] = cov / variance
    significant = [lag for lag, corr in result.items() if abs(corr) > 0.3]
    logger.info("Significant autocorrelations at lags: %s", significant)
    return result


def detect_seasonality(
    values: List[float], period: int = 5
) -> Dict[str, Any]:
    n = len(values)
    if n < period * 2:
        result: Dict[str, Any] = {"seasonal": False, "strength": 0.0, "period": period}
        logger.info("Not enough data for seasonality detection")
        return result

    seasonal_means: List[float] = []
    for p in range(period):
        positions = [float(values[i]) for i in range(p, n, period)]
        seasonal_means.append(float(np.mean(positions)))

    overall_mean = float(np.mean(values))
    seasonal_variance = float(np.var(seasonal_means))
    total_variance = float(np.var(values))

    strength = seasonal_variance / total_variance if total_variance > 0 else 0.0
    seasonal = bool(strength > 0.1)

    result = {"seasonal": seasonal, "strength": round(strength, 4), "period": period}
    logger.info("Seasonality detected: %s (strength=%.4f)", seasonal, strength)
    return result


def calculate_volatility_regime(
    values: List[float], window: int = 20
) -> Dict[str, Any]:
    if len(values) < 2:
        return {"regime": "low", "current_vol": 0.0, "avg_vol": 0.0}

    returns = [
        (float(values[i]) - float(values[i - 1])) / float(values[i - 1])
        for i in range(1, len(values))
        if float(values[i - 1]) != 0
    ]

    if not returns:
        return {"regime": "low", "current_vol": 0.0, "avg_vol": 0.0}

    recent = returns[-window:] if len(returns) >= window else returns
    current_vol = float(np.std(recent)) * 100.0
    avg_vol = float(np.std(returns)) * 100.0

    if current_vol < 1.0:
        regime = "low"
    elif current_vol <= 2.0:
        regime = "medium"
    else:
        regime = "high"

    result: Dict[str, Any] = {
        "regime": regime,
        "current_vol": round(current_vol, 4),
        "avg_vol": round(avg_vol, 4),
    }
    logger.info("Volatility regime: %s (current=%.4f%%)", regime, current_vol)
    return result


def detect_trend(values: List[float], window: int = 20) -> Dict[str, Any]:
    recent = values[-window:] if len(values) >= window else values
    n = len(recent)
    if n < 2:
        return {"trend": "sideways", "slope": 0.0, "r_squared": 0.0}

    x = list(range(n))
    x_mean = float(np.mean(x))
    y_mean = float(np.mean(recent))

    numerator = sum((float(x[i]) - x_mean) * (float(recent[i]) - y_mean) for i in range(n))
    denominator = sum((float(x[i]) - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator != 0 else 0.0

    y_pred = [slope * float(x[i]) + (y_mean - slope * x_mean) for i in range(n)]
    ss_res = sum((float(recent[i]) - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((float(recent[i]) - y_mean) ** 2 for i in range(n))
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

    normalized_slope = slope / y_mean if y_mean != 0 else slope
    if normalized_slope > 0.001:
        trend = "uptrend"
    elif normalized_slope < -0.001:
        trend = "downtrend"
    else:
        trend = "sideways"

    result: Dict[str, Any] = {
        "trend": trend,
        "slope": round(slope, 6),
        "r_squared": round(r_squared, 4),
    }
    logger.info("Trend detected: %s (slope=%.6f, R2=%.4f)", trend, slope, r_squared)
    return result


def calculate_drawdown_series(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"max_drawdown": 0.0, "current_drawdown": 0.0, "drawdown_series": []}

    peak = float(values[0])
    drawdown_series: List[float] = []
    for v in values:
        val = float(v)
        if val > peak:
            peak = val
        dd = (val - peak) / peak if peak != 0 else 0.0
        drawdown_series.append(round(dd, 6))

    max_drawdown = float(min(drawdown_series))
    current_drawdown = float(drawdown_series[-1])

    result: Dict[str, Any] = {
        "max_drawdown": round(max_drawdown, 6),
        "current_drawdown": round(current_drawdown, 6),
        "drawdown_series": drawdown_series,
    }
    logger.info("Max drawdown: %.4f%%", max_drawdown * 100)
    return result


def run_timeseries_analysis(
    ticker: str, prices: List[float], bucket: str
) -> Dict[str, Any]:
    autocorr = calculate_autocorrelation(prices)
    seasonality = detect_seasonality(prices)
    volatility = calculate_volatility_regime(prices)
    trend = detect_trend(prices)
    drawdown = calculate_drawdown_series(prices)

    result: Dict[str, Any] = {
        "ticker": ticker,
        "price_count": len(prices),
        "autocorrelation": {str(k): v for k, v in autocorr.items()},
        "seasonality": seasonality,
        "volatility": volatility,
        "trend": trend,
        "drawdown": {
            "max_drawdown": drawdown["max_drawdown"],
            "current_drawdown": drawdown["current_drawdown"],
        },
        "analyzed_at": datetime.datetime.utcnow().isoformat(),
    }

    now = datetime.datetime.utcnow()
    s3_key = "processed/timeseries/{}/{}/{}/{}.json".format(
        now.strftime("%Y"),
        now.strftime("%m"),
        now.strftime("%d"),
        ticker,
    )

    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=json.dumps(result),
            ContentType="application/json",
        )
        logger.info("Saved time series analysis to s3://%s/%s", bucket, s3_key)
    except Exception as e:
        logger.warning("S3 upload skipped: %s", str(e))

    logger.info("Time Series Analysis Complete for %s", ticker)
    return result


if __name__ == "__main__":
    pass
