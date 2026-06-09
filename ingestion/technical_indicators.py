import json
import logging
import os
from datetime import datetime, timedelta

import boto3
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_sma(prices: list, window: int) -> list:
    """
    Calculate Simple Moving Average.

    Args:
        prices: List of price values.
        window: Lookback period.

    Returns:
        List of SMA values, with None for the first window-1 positions.
    """
    result: list = [None] * (window - 1)
    for i in range(window - 1, len(prices)):
        sma = sum(prices[i - window + 1 : i + 1]) / window
        result.append(sma)
    return result


def calculate_rsi(prices: list, period: int = 14) -> list:
    """
    Calculate Relative Strength Index.

    Args:
        prices: List of price values.
        period: RSI lookback period (default 14).

    Returns:
        List of RSI values (0–100), with None for the first period positions.
    """
    if len(prices) < period + 1:
        return [None] * len(prices)

    result: list = [None] * period

    gains = [max(prices[i] - prices[i - 1], 0) for i in range(1, period + 1)]
    losses = [max(prices[i - 1] - prices[i], 0) for i in range(1, period + 1)]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(round(100 - (100 / (1 + rs)), 4))

    for i in range(period + 1, len(prices)):
        gain = max(prices[i] - prices[i - 1], 0)
        loss = max(prices[i - 1] - prices[i], 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(round(100 - (100 / (1 + rs)), 4))

    return result


def calculate_bollinger_bands(
    prices: list,
    window: int = 20,
    num_std: float = 2.0,
) -> dict:
    """
    Calculate Bollinger Bands.

    Args:
        prices: List of price values.
        window: SMA lookback period (default 20).
        num_std: Number of standard deviations for band width (default 2.0).

    Returns:
        Dict with upper_band, middle_band, and lower_band lists.
    """
    middle = calculate_sma(prices, window)
    upper: list = [None] * (window - 1)
    lower: list = [None] * (window - 1)

    for i in range(window - 1, len(prices)):
        window_prices = prices[i - window + 1 : i + 1]
        std = float(np.std(window_prices, ddof=1))
        upper.append(middle[i] + num_std * std)
        lower.append(middle[i] - num_std * std)

    return {"upper_band": upper, "middle_band": middle, "lower_band": lower}


def _ema(values: list, period: int) -> list:
    """Compute EMA on a list, padding with None for the first period-1 positions."""
    if len(values) < period:
        return [None] * len(values)
    k = 2.0 / (period + 1)
    result: list = [None] * (period - 1)
    result.append(sum(values[:period]) / period)
    for i in range(period, len(values)):
        result.append(values[i] * k + result[-1] * (1 - k))
    return result


def calculate_macd(
    prices: list,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict:
    """
    Calculate MACD (Moving Average Convergence/Divergence).

    Args:
        prices: List of price values.
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal line EMA period (default 9).

    Returns:
        Dict with macd_line, signal_line, and histogram lists.
    """
    ema_fast = _ema(prices, fast)
    ema_slow = _ema(prices, slow)

    macd_line = [None if (f is None or s is None) else f - s for f, s in zip(ema_fast, ema_slow)]

    valid_start = next((i for i, v in enumerate(macd_line) if v is not None), len(macd_line))
    valid_macd = [v for v in macd_line if v is not None]
    signal_values = _ema(valid_macd, signal)
    signal_line = [None] * valid_start + signal_values

    histogram = [
        None if (m is None or s is None) else m - s for m, s in zip(macd_line, signal_line)
    ]

    return {"macd_line": macd_line, "signal_line": signal_line, "histogram": histogram}


def run_technical_analysis(ticker: str, bucket: str) -> dict:
    """
    Load 60 days of historical prices, calculate all indicators, and save to S3.

    Args:
        ticker: Stock ticker symbol.
        bucket: S3 bucket name.

    Returns:
        Dict containing all calculated technical indicators.
    """
    s3 = boto3.client("s3")
    today = datetime.utcnow()
    close_prices: list = []

    for i in range(60):
        day = today - timedelta(days=i + 1)
        date_str = day.strftime("%Y/%m/%d")
        key = f"raw/stocks/{date_str}/{ticker}.json"
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            data = json.loads(response["Body"].read().decode("utf-8"))
            df = pd.DataFrame(data)
            df.columns = [col.lower() for col in df.columns]
            close_prices.insert(0, float(df["close"].iloc[0]))
        except Exception:
            continue

    if not close_prices:
        logger.warning("No historical prices found for %s", ticker)
        return {}

    results = {
        "ticker": ticker,
        "date": today.strftime("%Y-%m-%d"),
        "price_count": len(close_prices),
        "sma_20": calculate_sma(close_prices, window=20),
        "sma_50": calculate_sma(close_prices, window=50),
        "rsi": calculate_rsi(close_prices),
        "bollinger": calculate_bollinger_bands(close_prices),
        "macd": calculate_macd(close_prices),
    }

    date_path = today.strftime("%Y/%m/%d")
    s3_key = f"processed/technical/{date_path}/{ticker}.json"
    try:
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=json.dumps(results),
            ContentType="application/json",
        )
        logger.info("Technical analysis saved to s3://%s/%s", bucket, s3_key)
    except Exception as e:
        logger.error("Failed to save technical analysis for %s: %s", ticker, e)

    return results


if __name__ == "__main__":
    _bucket = os.getenv("AWS_BUCKET_NAME", "")
