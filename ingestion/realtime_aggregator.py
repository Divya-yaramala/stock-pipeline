import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def aggregate_ohlcv(
    prices: List[Dict[str, Any]],
    window_minutes: int = 5,
) -> List[Dict[str, Any]]:
    if not prices:
        return []

    bars: List[Dict[str, Any]] = []
    current_bar: Optional[Dict[str, Any]] = None
    current_bar_start: Optional[datetime] = None

    for entry in prices:
        ts_str = str(entry["timestamp"])
        ts = datetime.fromisoformat(ts_str)
        price = float(str(entry["price"]))
        volume = int(str(entry.get("volume", 0)))

        if current_bar_start is None:
            current_bar_start = ts
            current_bar = {
                "timestamp": ts_str,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
                "bar_count": 1,
            }
            continue

        elapsed_minutes = (ts - current_bar_start).total_seconds() / 60.0
        if elapsed_minutes < window_minutes and current_bar is not None:
            current_bar["high"] = max(float(str(current_bar["high"])), price)
            current_bar["low"] = min(float(str(current_bar["low"])), price)
            current_bar["close"] = price
            current_bar["volume"] = int(str(current_bar["volume"])) + volume
            current_bar["bar_count"] = int(str(current_bar["bar_count"])) + 1
        else:
            if current_bar is not None:
                bars.append(current_bar)
            current_bar_start = ts
            current_bar = {
                "timestamp": ts_str,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
                "bar_count": 1,
            }

    if current_bar is not None:
        bars.append(current_bar)

    logger.info(f"OHLCV aggregation complete: {len(bars)} bars created from {len(prices)} ticks")
    return bars


def calculate_vwap(prices: List[Dict[str, Any]]) -> float:
    total_pv = 0.0
    total_volume = 0.0
    for entry in prices:
        price = float(str(entry["price"]))
        volume = float(str(entry.get("volume", 0)))
        total_pv += price * volume
        total_volume += volume

    vwap = total_pv / total_volume if total_volume > 0 else 0.0
    logger.info(f"VWAP calculated: {vwap:.4f}")
    return round(vwap, 4)


def calculate_volume_profile(
    prices: List[Dict[str, Any]],
    num_buckets: int = 10,
) -> Dict[str, Any]:
    if not prices:
        return {"buckets": [], "poc": 0.0}

    price_list = [float(str(e["price"])) for e in prices]
    volume_list = [float(str(e.get("volume", 0))) for e in prices]

    min_price = min(price_list)
    max_price = max(price_list)
    bucket_size = (max_price - min_price) / num_buckets if max_price != min_price else 1.0

    buckets: List[Dict[str, Any]] = []
    for i in range(num_buckets):
        low = min_price + i * bucket_size
        high = low + bucket_size
        bucket_volume = 0.0
        for price, vol in zip(price_list, volume_list):
            if low <= price < high or (i == num_buckets - 1 and price == max_price):
                bucket_volume += vol
        buckets.append({"price_low": round(low, 4), "price_high": round(high, 4), "volume": bucket_volume})

    poc_bucket = max(buckets, key=lambda b: float(str(b["volume"])))
    poc = (float(str(poc_bucket["price_low"])) + float(str(poc_bucket["price_high"]))) / 2.0

    result: Dict[str, Any] = {"buckets": buckets, "poc": round(poc, 4)}
    logger.info(f"Volume profile: {num_buckets} buckets, POC={poc:.4f}")
    return result


def detect_momentum(
    prices: List[float],
    short_period: int = 5,
    long_period: int = 20,
) -> Dict[str, Any]:
    if len(prices) < long_period:
        return {"momentum": "neutral", "short_ma": 0.0, "long_ma": 0.0}

    short_ma = sum(prices[-short_period:]) / short_period
    long_ma = sum(prices[-long_period:]) / long_period

    if short_ma > long_ma:
        momentum = "bullish"
    elif short_ma < long_ma:
        momentum = "bearish"
    else:
        momentum = "neutral"

    result: Dict[str, Any] = {
        "momentum": momentum,
        "short_ma": round(short_ma, 4),
        "long_ma": round(long_ma, 4),
    }
    logger.info(f"Momentum signal: {momentum} (short_ma={short_ma:.4f}, long_ma={long_ma:.4f})")
    return result


def run_realtime_aggregation(
    ticker: str,
    prices: List[Dict[str, Any]],
    bucket: str,
) -> Dict[str, Any]:
    bars = aggregate_ohlcv(prices)
    vwap = calculate_vwap(prices)
    volume_profile = calculate_volume_profile(prices)
    price_floats = [float(str(e["price"])) for e in prices]
    momentum = detect_momentum(price_floats)

    results: Dict[str, Any] = {
        "ticker": ticker,
        "bars": bars,
        "vwap": vwap,
        "volume_profile": volume_profile,
        "momentum": momentum,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        now = datetime.utcnow()
        key = f"streaming/aggregations/{now.year}/{now.month:02d}/{now.day:02d}/{ticker}.json"
        s3_client.put_object(Bucket=bucket, Key=key, Body=json.dumps(results, default=str))
        logger.info(f"Real-Time Aggregation Complete for {ticker} saved to s3://{bucket}/{key}")
    except Exception as e:
        logger.error(f"Failed to save aggregation for {ticker}: {e}")

    logger.info(f"Real-Time Aggregation Complete for {ticker}")
    return results


if __name__ == "__main__":
    pass
