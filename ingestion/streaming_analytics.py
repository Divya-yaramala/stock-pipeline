import json
import logging
import os
from collections import deque
from typing import Any, Deque, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def create_sliding_window(window_size: int = 20) -> Deque:
    window: Deque = deque(maxlen=window_size)
    logger.info(f"Sliding window created with maxlen={window_size}")
    return window


def update_window(window: Deque, value: float) -> Deque:
    window.append(value)
    return window


def calculate_window_stats(window: Deque) -> Dict[str, float]:
    values = list(window)
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std = variance**0.5
    latest = values[-1]
    oldest = values[0]
    change_pct = (latest - oldest) / oldest * 100 if oldest != 0 else 0.0
    stats: Dict[str, float] = {
        "mean": mean,
        "std": std,
        "min": float(min(values)),
        "max": float(max(values)),
        "latest": latest,
        "change_pct": change_pct,
    }
    logger.info(f"Window stats: mean={mean:.2f}, std={std:.2f}, change_pct={change_pct:.2f}%")
    return stats


def detect_streaming_anomaly(
    window: Deque,
    z_score_threshold: float = 2.5,
) -> Dict[str, Any]:
    values = list(window)
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std = variance**0.5

    latest = values[-1]
    z_score = (latest - mean) / std if std > 0 else 0.0
    is_anomaly = abs(z_score) > z_score_threshold

    if not is_anomaly:
        direction = "normal"
    elif z_score > 0:
        direction = "spike"
    else:
        direction = "drop"

    result: Dict[str, Any] = {
        "is_anomaly": is_anomaly,
        "z_score": round(z_score, 4),
        "direction": direction,
    }
    logger.info(
        f"Anomaly detection: is_anomaly={is_anomaly}, z_score={z_score:.4f}, direction={direction}"
    )
    return result


def calculate_streaming_rsi(
    window: Deque,
    period: int = 14,
) -> Optional[float]:
    values = list(window)
    if len(values) < period + 1:
        logger.info(f"Insufficient data for RSI: need {period + 1} points, have {len(values)}")
        return None

    recent = values[-(period + 1) :]
    gains = []
    losses = []
    for i in range(1, len(recent)):
        diff = recent[i] - recent[i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(diff))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

    logger.info(f"RSI calculated: {rsi:.2f}")
    return round(rsi, 2)


def process_price_stream(
    ticker: str,
    prices: List[float],
    window_size: int = 20,
) -> Dict[str, Any]:
    window = create_sliding_window(window_size)
    anomaly_count = 0
    final_stats: Dict[str, float] = {}

    for price in prices:
        update_window(window, price)
        if len(window) >= 2:
            stats = calculate_window_stats(window)
            final_stats = stats
            if len(window) >= 3:
                result = detect_streaming_anomaly(window)
                if bool(result["is_anomaly"]):
                    anomaly_count += 1

    summary: Dict[str, Any] = {
        "ticker": ticker,
        "processed": len(prices),
        "anomalies": anomaly_count,
        "final_stats": final_stats,
    }
    logger.info(
        f"Stream processing complete for {ticker}: "
        f"processed={len(prices)}, anomalies={anomaly_count}"
    )
    return summary


def save_stream_results(
    ticker: str,
    results: Dict[str, Any],
    bucket: str,
    date: str,
) -> bool:
    try:
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        parts = date.split("-")
        year = str(parts[0])
        month = str(parts[1])
        day = str(parts[2])
        key = f"streaming/analytics/{year}/{month}/{day}/{ticker}.json"
        payload = json.dumps(results, default=str)
        s3_client.put_object(Bucket=bucket, Key=key, Body=payload)
        logger.info(f"Stream results saved to s3://{bucket}/{key}")
        return True
    except Exception as e:
        logger.error(f"Failed to save stream results for {ticker}: {e}")
        return False


if __name__ == "__main__":
    pass
