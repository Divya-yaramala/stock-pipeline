import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def calculate_distribution_stats(values: List[float]) -> Dict[str, float]:
    series = pd.Series(values)
    stats: Dict[str, float] = {
        "mean": float(series.mean()),
        "std": float(series.std()),
        "min": float(series.min()),
        "max": float(series.max()),
        "median": float(series.median()),
    }
    logger.info("Distribution stats: mean=%.4f std=%.4f", stats["mean"], stats["std"])
    return stats


def calculate_psi(baseline: List[float], current: List[float], buckets: int = 10) -> float:
    baseline_arr = np.array(baseline)
    current_arr = np.array(current)

    min_val = float(min(baseline_arr.min(), current_arr.min()))
    max_val = float(max(baseline_arr.max(), current_arr.max()))

    if max_val == min_val:
        max_val = min_val + 1.0

    bins = np.linspace(min_val, max_val, buckets + 1)

    baseline_counts, _ = np.histogram(baseline_arr, bins=bins)
    current_counts, _ = np.histogram(current_arr, bins=bins)

    epsilon = 1e-6
    baseline_pct = baseline_counts / len(baseline_arr) + epsilon
    current_pct = current_counts / len(current_arr) + epsilon

    psi = float(np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct)))
    logger.info("Calculated PSI: %.4f", psi)
    return psi


def detect_feature_drift(
    ticker: str,
    feature_name: str,
    baseline_bucket: str,
    current_values: List[float],
    bucket: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    key = f"models/baselines/{ticker}_{feature_name}.json"

    baseline_values: Optional[List[float]] = None
    try:
        response = s3.get_object(Bucket=baseline_bucket, Key=key)
        data = json.loads(response["Body"].read().decode("utf-8"))
        baseline_values = [float(str(v)) for v in data.get("values", [])]
    except Exception as e:
        logger.warning("No baseline found for %s/%s: %s", ticker, feature_name, e)

    if not baseline_values or not current_values:
        psi_score = 0.0
    else:
        psi_score = calculate_psi(baseline_values, current_values)

    if psi_score < 0.1:
        severity = "none"
    elif psi_score < 0.25:
        severity = "moderate"
    else:
        severity = "significant"

    result: Dict[str, Any] = {
        "feature": feature_name,
        "psi_score": psi_score,
        "drift_detected": psi_score >= 0.1,
        "severity": severity,
    }
    logger.info(
        "Feature drift for %s/%s: PSI=%.4f severity=%s",
        ticker,
        feature_name,
        psi_score,
        severity,
    )
    return result


def detect_prediction_drift(
    ticker: str,
    baseline_predictions: List[float],
    current_predictions: List[float],
) -> Dict[str, Any]:
    baseline_mean = float(np.mean(np.array(baseline_predictions)))
    current_mean = float(np.mean(np.array(current_predictions)))

    if baseline_mean == 0:
        mean_shift_pct = 0.0
    else:
        mean_shift_pct = float(abs(current_mean - baseline_mean) / abs(baseline_mean) * 100)

    drift_detected = mean_shift_pct > 10.0

    result: Dict[str, Any] = {
        "mean_shift_pct": mean_shift_pct,
        "drift_detected": drift_detected,
    }
    logger.info(
        "Prediction drift for %s: %.2f%% shift detected=%s",
        ticker,
        mean_shift_pct,
        drift_detected,
    )
    return result


def should_trigger_retraining(drift_results: List[Dict[str, Any]]) -> bool:
    significant = [r for r in drift_results if str(r.get("severity", "")) == "significant"]
    moderate = [r for r in drift_results if str(r.get("severity", "")) == "moderate"]

    if significant:
        logger.info("Retraining triggered: %d feature(s) with significant drift", len(significant))
        return True
    if len(moderate) > 2:
        logger.info("Retraining triggered: %d features with moderate drift", len(moderate))
        return True

    logger.info("No retraining needed: drift within acceptable thresholds")
    return False


def run_drift_detection(ticker: str, bucket: str) -> Dict[str, Any]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    today = datetime.now().strftime("%Y/%m/%d")
    date_dash = datetime.now().strftime("%Y-%m-%d")

    drift_results: List[Dict[str, Any]] = []
    raw_key = f"raw/stocks/{today}/{ticker}.json"

    try:
        response = s3.get_object(Bucket=bucket, Key=raw_key)
        raw_data = json.loads(response["Body"].read().decode("utf-8"))

        df = pd.DataFrame.from_dict(raw_data, orient="index")

        for feature_name in ["close", "open", "high", "low", "volume"]:
            if feature_name in raw_data:
                feature_dict = raw_data[feature_name]
                current_values = [float(str(v)) for v in feature_dict.values()]
                result = detect_feature_drift(ticker, feature_name, bucket, current_values, bucket)
                drift_results.append(result)

        _ = df  # used for potential future column-based processing
    except Exception as e:
        logger.warning("Could not load raw data for %s: %s", ticker, e)

    retrain_needed = should_trigger_retraining(drift_results)

    report: Dict[str, Any] = {
        "ticker": ticker,
        "date": date_dash,
        "drift_results": drift_results,
        "retrain_needed": retrain_needed,
        "created_at": datetime.now().isoformat(),
    }

    report_key = f"models/drift/{today}/{ticker}.json"
    try:
        s3.put_object(Bucket=bucket, Key=report_key, Body=json.dumps(report))
    except Exception as e:
        logger.error("Failed to save drift report: %s", e)

    logger.info("Drift Detection Complete: retrain=%s", retrain_needed)
    return report


if __name__ == "__main__":
    pass
