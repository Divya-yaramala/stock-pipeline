import datetime
import json
import logging
from typing import Any, Dict, List

import boto3

from ingestion.online_feature_engineer import build_online_feature_vector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_model_weights(
    current_weights: Dict[str, float],
    recent_accuracy: float,
    learning_rate: float = 0.01,
) -> Dict[str, float]:
    updated: Dict[str, float] = {}
    for model, weight in current_weights.items():
        adjustment = learning_rate * (recent_accuracy - 0.5)
        updated[model] = max(0.0, min(1.0, weight + adjustment))
    total = sum(updated.values())
    if total > 0:
        updated = {k: v / total for k, v in updated.items()}
    logger.info("Model weights updated with accuracy=%.3f", recent_accuracy)
    return updated


def detect_concept_drift(
    recent_errors: List[float],
    baseline_error: float,
    threshold: float = 0.2,
) -> Dict[str, Any]:
    avg_recent = sum(recent_errors) / len(recent_errors) if recent_errors else baseline_error
    error_increase_pct = float(
        (avg_recent - baseline_error) / baseline_error if baseline_error != 0 else 0.0
    )
    drift_detected = error_increase_pct > threshold
    if drift_detected:
        action = "retrain"
    elif error_increase_pct > threshold / 2:
        action = "adjust_weights"
    else:
        action = "continue"
    result: Dict[str, Any] = {
        "drift_detected": drift_detected,
        "error_increase_pct": error_increase_pct,
        "action": action,
    }
    logger.info("Concept drift check: drift=%s, action=%s", drift_detected, action)
    return result


def select_best_model_for_regime(
    regime: str,
    model_performance: Dict[str, Dict[str, float]],
) -> str:
    regime_map: Dict[str, str] = {
        "trending": "gradient_boosting",
        "volatile": "ensemble",
        "mean_reverting": "linear_regression",
        "sideways": "linear_regression",
    }
    model_name = regime_map.get(regime, "ensemble")
    logger.info("Model selected for regime '%s': %s", regime, model_name)
    return model_name


def calculate_adaptive_prediction(
    ticker: str,
    regime: str,
    features: Dict[str, float],
    model_weights: Dict[str, float],
    bucket: str,
) -> Dict[str, Any]:
    model_performance: Dict[str, Dict[str, float]] = {
        "gradient_boosting": {"accuracy": float(model_weights.get("gradient_boosting", 0.33))},
        "ensemble": {"accuracy": float(model_weights.get("ensemble", 0.33))},
        "linear_regression": {"accuracy": float(model_weights.get("linear_regression", 0.34))},
    }
    model_used = select_best_model_for_regime(regime, model_performance)
    price_mean = float(features.get("price_mean", 100.0))
    momentum = float(features.get("price_momentum", 0.0))
    prediction = price_mean * (1 + momentum * float(model_weights.get(model_used, 0.33)))
    result: Dict[str, Any] = {
        "ticker": ticker,
        "prediction": prediction,
        "model_used": model_used,
        "regime": regime,
    }
    logger.info(
        "Adaptive prediction made for %s: model=%s, prediction=%.4f", ticker, model_used, prediction
    )
    return result


def run_adaptive_modeling(
    ticker: str,
    prices: List[float],
    volumes: List[float],
    bucket: str,
) -> Dict[str, Any]:
    vector = build_online_feature_vector(ticker, prices, volumes)
    regime = str(vector["regime"])
    features = dict(vector["features"])
    model_weights: Dict[str, float] = {
        "gradient_boosting": 0.33,
        "ensemble": 0.34,
        "linear_regression": 0.33,
    }
    prediction = calculate_adaptive_prediction(ticker, regime, features, model_weights, bucket)
    result: Dict[str, Any] = {
        "ticker": ticker,
        "regime": regime,
        "prediction": prediction,
        "feature_count": len(features),
        "computed_at": datetime.datetime.utcnow().isoformat(),
    }
    now = datetime.datetime.utcnow()
    date_path = now.strftime("%Y/%m/%d")
    key = f"models/adaptive/{date_path}/{ticker}.json"
    try:
        client = boto3.client("s3")
        client.put_object(Bucket=bucket, Key=key, Body=json.dumps(result))
        logger.info("Adaptive model results saved: s3://%s/%s", bucket, key)
    except Exception as exc:
        logger.error("Failed to save adaptive model results: %s", exc)
    logger.info("Adaptive Modeling Complete for %s", ticker)
    return result


if __name__ == "__main__":
    pass
