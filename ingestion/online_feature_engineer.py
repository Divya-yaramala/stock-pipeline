import datetime
import json
import logging
import math
from typing import Any, Dict, List

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def compute_rolling_features(
    price_window: List[float],
    volume_window: List[float],
) -> Dict[str, float]:
    n = len(price_window)
    price_mean = sum(price_window) / n
    price_variance = sum((p - price_mean) ** 2 for p in price_window) / n
    price_std = math.sqrt(price_variance)
    price_momentum = (price_window[-1] / price_window[0]) - 1 if price_window[0] != 0 else 0.0
    volume_mean = sum(volume_window) / len(volume_window)
    volume_ratio = (volume_window[-1] / volume_mean) if volume_mean != 0 else 1.0
    mid = n // 2
    early_momentum = (price_window[mid] / price_window[0]) - 1 if price_window[0] != 0 else 0.0
    price_acceleration = price_momentum - early_momentum
    features = {
        "price_mean": price_mean,
        "price_std": price_std,
        "price_momentum": price_momentum,
        "volume_mean": volume_mean,
        "volume_ratio": volume_ratio,
        "price_acceleration": price_acceleration,
    }
    logger.info("Rolling features computed: %d price points", n)
    return features


def compute_microstructure_features(
    prices: List[float],
    volumes: List[float],
) -> Dict[str, float]:
    close = prices[-1]
    high = max(prices)
    low = min(prices)
    bid_ask_spread_proxy = (high - low) / close if close != 0 else 0.0
    price_changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    avg_price_change = (
        sum(abs(c) for c in price_changes) / len(price_changes) if price_changes else 0.0
    )
    avg_volume = sum(volumes) / len(volumes)
    price_impact = avg_volume * avg_price_change
    time_period = float(len(volumes))
    trade_intensity = avg_volume / time_period if time_period > 0 else 0.0
    result = {
        "bid_ask_spread_proxy": bid_ask_spread_proxy,
        "price_impact": price_impact,
        "trade_intensity": trade_intensity,
    }
    logger.info("Microstructure features computed")
    return result


def compute_regime_features(prices: List[float]) -> Dict[str, Any]:
    n = len(prices)
    mean = sum(prices) / n
    std = math.sqrt(sum((p - mean) ** 2 for p in prices) / n)
    momentum = (prices[-1] / prices[0]) - 1 if prices[0] != 0 else 0.0
    autocorr = 0.0
    if n > 2:
        shifted = prices[:-1]
        original = prices[1:]
        shifted_mean = sum(shifted) / len(shifted)
        original_mean = sum(original) / len(original)
        numerator = sum(
            (shifted[i] - shifted_mean) * (original[i] - original_mean) for i in range(len(shifted))
        )
        denom_a = math.sqrt(sum((v - shifted_mean) ** 2 for v in shifted))
        denom_b = math.sqrt(sum((v - original_mean) ** 2 for v in original))
        denom = denom_a * denom_b
        autocorr = numerator / denom if denom != 0 else 0.0
    trending = abs(momentum) > 0.02
    volatile = (std / mean) > 0.03 if mean != 0 else False
    mean_reverting = autocorr < -0.3
    if trending:
        regime = "trending"
        confidence = min(1.0, abs(momentum) / 0.05)
    elif volatile:
        regime = "volatile"
        confidence = min(1.0, (std / mean) / 0.06) if mean != 0 else 0.5
    elif mean_reverting:
        regime = "mean_reverting"
        confidence = min(1.0, abs(autocorr) / 0.6)
    else:
        regime = "sideways"
        confidence = 0.5
    features = {
        "momentum": momentum,
        "volatility_ratio": std / mean if mean != 0 else 0.0,
        "autocorrelation": autocorr,
    }
    logger.info("Regime detected: %s (confidence=%.2f)", regime, confidence)
    return {"regime": regime, "confidence": confidence, "features": features}


def build_online_feature_vector(
    ticker: str,
    recent_prices: List[float],
    recent_volumes: List[float],
) -> Dict[str, Any]:
    rolling = compute_rolling_features(recent_prices, recent_volumes)
    micro = compute_microstructure_features(recent_prices, recent_volumes)
    regime_result = compute_regime_features(recent_prices)
    all_features: Dict[str, float] = {}
    all_features.update(rolling)
    all_features.update(micro)
    all_features.update({str(k): float(v) for k, v in regime_result["features"].items()})
    vector: Dict[str, Any] = {
        "ticker": ticker,
        "features": all_features,
        "regime": str(regime_result["regime"]),
        "computed_at": datetime.datetime.utcnow().isoformat(),
    }
    logger.info("Feature vector built for %s: regime=%s", ticker, vector["regime"])
    return vector


def save_online_features(
    ticker: str,
    feature_vector: Dict[str, Any],
    bucket: str,
) -> bool:
    now = datetime.datetime.utcnow()
    date_path = now.strftime("%Y/%m/%d")
    timestamp = now.strftime("%H%M%S")
    key = f"features/online/{date_path}/{ticker}_{timestamp}.json"
    try:
        client = boto3.client("s3")
        client.put_object(Bucket=bucket, Key=key, Body=json.dumps(feature_vector))
        logger.info("Online features saved: s3://%s/%s", bucket, key)
        return True
    except Exception as exc:
        logger.error("Failed to save online features: %s", exc)
        return False


def run_online_feature_engineering(
    ticker: str,
    prices: List[float],
    volumes: List[float],
    bucket: str,
) -> Dict[str, Any]:
    vector = build_online_feature_vector(ticker, prices, volumes)
    save_online_features(ticker, vector, bucket)
    logger.info("Online Feature Engineering Complete for %s", ticker)
    return vector


if __name__ == "__main__":
    pass
