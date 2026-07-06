import json
import logging
from datetime import datetime
from typing import Any, Dict, List

import boto3
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_prediction_actuals(
    ticker: str,
    bucket: str,
    date: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    key = f"models/monitoring/{date}/actuals/{ticker}.json"
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        data: Dict[str, Any] = json.loads(response["Body"].read().decode("utf-8"))
        logger.info("Loaded prediction actuals for %s on %s", ticker, date)
        return data
    except Exception:
        logger.info("No actuals found for %s on %s, returning empty", ticker, date)
        return {"ticker": ticker, "predictions": [], "actuals": []}


def calculate_model_metrics(
    predictions: List[float],
    actuals: List[float],
) -> Dict[str, float]:
    preds = np.array(predictions, dtype=float)
    acts = np.array(actuals, dtype=float)

    mae = float(np.mean(np.abs(preds - acts)))
    rmse = float(np.sqrt(np.mean((preds - acts) ** 2)))

    nonzero = acts != 0
    mape = (
        float(np.mean(np.abs((preds[nonzero] - acts[nonzero]) / acts[nonzero])) * 100)
        if nonzero.any()
        else 0.0
    )

    ss_res = float(np.sum((acts - preds) ** 2))
    ss_tot = float(np.sum((acts - np.mean(acts)) ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot != 0 else 1.0

    metrics = {"MAE": mae, "RMSE": rmse, "MAPE": mape, "R2": r2}
    logger.info("Metrics calculated: MAE=%.4f RMSE=%.4f MAPE=%.4f R2=%.4f", mae, rmse, mape, r2)
    return metrics


def detect_performance_degradation(
    current_metrics: Dict[str, float],
    baseline_metrics: Dict[str, float],
    threshold_pct: float = 20.0,
) -> Dict[str, Any]:
    current_rmse = float(str(current_metrics.get("RMSE", 0.0)))
    baseline_rmse = float(str(baseline_metrics.get("RMSE", 0.0)))

    if baseline_rmse == 0:
        pct_change = 0.0
    else:
        pct_change = ((current_rmse - baseline_rmse) / baseline_rmse) * 100

    degraded = pct_change > threshold_pct

    if not degraded:
        severity = "none"
    elif pct_change < 50.0:
        severity = "warning"
    else:
        severity = "critical"

    comparison = {
        "current_rmse": current_rmse,
        "baseline_rmse": baseline_rmse,
        "pct_change": round(pct_change, 2),
    }

    logger.info(
        "Performance status: degraded=%s severity=%s pct_change=%.2f%%",
        degraded,
        severity,
        pct_change,
    )
    return {"degraded": degraded, "metrics_comparison": comparison, "severity": severity}


def save_monitoring_report(
    ticker: str,
    metrics: Dict[str, float],
    degradation: Dict[str, Any],
    bucket: str,
    date: str,
) -> bool:
    s3 = boto3.client("s3")
    key = f"models/monitoring/{date}/{ticker}.json"
    report = {
        "ticker": ticker,
        "date": date,
        "metrics": metrics,
        "degradation": degradation,
        "saved_at": datetime.utcnow().isoformat(),
    }
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(report),
            ContentType="application/json",
        )
        logger.info("Monitoring report saved to s3://%s/%s", bucket, key)
        return True
    except Exception as e:
        logger.error("Failed to save monitoring report: %s", e)
        return False


def run_model_monitoring(
    ticker: str,
    bucket: str,
) -> Dict[str, Any]:
    date = datetime.utcnow().strftime("%Y/%m/%d")
    data = load_prediction_actuals(ticker, bucket, date)

    predictions: List[float] = [float(str(v)) for v in data.get("predictions", [])]
    actuals: List[float] = [float(str(v)) for v in data.get("actuals", [])]

    if predictions and actuals:
        metrics = calculate_model_metrics(predictions, actuals)
    else:
        metrics = {"MAE": 0.0, "RMSE": 0.0, "MAPE": 0.0, "R2": 0.0}

    baseline: Dict[str, float] = {"MAE": 5.0, "RMSE": 8.0, "MAPE": 3.0, "R2": 0.85}
    degradation = detect_performance_degradation(metrics, baseline)

    save_monitoring_report(ticker, metrics, degradation, bucket, date)

    report: Dict[str, Any] = {
        "ticker": ticker,
        "date": date,
        "metrics": metrics,
        "degradation": degradation,
    }
    logger.info("Model Monitoring Complete: degraded=%s", degradation["degraded"])
    return report


if __name__ == "__main__":
    pass
