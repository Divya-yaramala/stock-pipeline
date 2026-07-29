import boto3
import json
import os
import logging
import math
from datetime import datetime
from typing import Optional, Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def predict_anomaly_probability(
    recent_prices: List[float],
    window: int = 10,
) -> float:
    if len(recent_prices) < 2:
        return 0.0
    window_prices = recent_prices[-window:] if len(recent_prices) >= window else recent_prices
    mean = sum(window_prices) / len(window_prices)
    variance = sum((p - mean) ** 2 for p in window_prices) / len(window_prices)
    std = math.sqrt(variance) if variance > 0 else 1e-9
    latest = recent_prices[-1]
    z_score = abs(latest - mean) / std
    probability = 1.0 / (1.0 + math.exp(-z_score + 2))
    logger.info(f"Anomaly probability: {probability:.4f} (z_score={z_score:.4f})")
    return float(probability)


def predict_quality_degradation(
    quality_scores: List[float],
    threshold: float = 80.0,
) -> Dict[str, Any]:
    if len(quality_scores) < 2:
        return {"degrading": False, "days_until_breach": None, "trend_slope": 0.0}

    n = len(quality_scores)
    x_mean = (n - 1) / 2.0
    y_mean = sum(quality_scores) / n
    numerator = sum((i - x_mean) * (quality_scores[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator != 0 else 0.0

    degrading = slope < 0
    days_until_breach: Optional[int] = None

    if degrading and quality_scores[-1] > threshold and slope != 0:
        days_float = (threshold - quality_scores[-1]) / slope
        days_until_breach = int(days_float) if days_float > 0 else None

    result: Dict[str, Any] = {
        "degrading": degrading,
        "days_until_breach": days_until_breach,
        "trend_slope": float(slope),
    }
    logger.info(f"Quality degradation prediction: {result}")
    return result


def predict_sla_risk(
    completion_times: List[float],
    sla_target_hour: int = 7,
) -> Dict[str, Any]:
    if len(completion_times) < 2:
        return {"at_risk": False, "predicted_completion_hour": 0.0, "confidence": "low"}

    n = len(completion_times)
    x_mean = (n - 1) / 2.0
    y_mean = sum(completion_times) / n
    numerator = sum((i - x_mean) * (completion_times[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator != 0 else 0.0

    predicted = completion_times[-1] + slope
    at_risk = predicted > float(sla_target_hour)

    confidence = "high" if len(completion_times) >= 7 else "medium" if len(completion_times) >= 4 else "low"

    result: Dict[str, Any] = {
        "at_risk": at_risk,
        "predicted_completion_hour": float(predicted),
        "confidence": confidence,
    }
    logger.info(f"SLA risk prediction: {result}")
    return result


def generate_predictive_alerts(
    ticker: str,
    metrics: Dict[str, Any],
    bucket: str,
) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []

    recent_prices: List[float] = [float(str(p)) for p in metrics.get("recent_prices", [])]
    if recent_prices:
        prob = predict_anomaly_probability(recent_prices)
        if prob > 0.7:
            alerts.append(
                {
                    "type": "anomaly_probability",
                    "severity": "HIGH" if prob > 0.9 else "MEDIUM",
                    "message": f"{ticker}: Anomaly probability {prob:.2%}",
                    "prediction": {"probability": prob},
                }
            )

    quality_scores: List[float] = [float(str(s)) for s in metrics.get("quality_scores", [])]
    if quality_scores:
        qd = predict_quality_degradation(quality_scores)
        if qd["degrading"]:
            alerts.append(
                {
                    "type": "quality_degradation",
                    "severity": "HIGH" if qd["days_until_breach"] is not None and int(str(qd["days_until_breach"])) <= 3 else "MEDIUM",
                    "message": f"{ticker}: Quality degrading, breach in {qd['days_until_breach']} days",
                    "prediction": qd,
                }
            )

    completion_times: List[float] = [float(str(t)) for t in metrics.get("completion_times", [])]
    if completion_times:
        sla = predict_sla_risk(completion_times)
        if sla["at_risk"]:
            alerts.append(
                {
                    "type": "sla_risk",
                    "severity": "HIGH",
                    "message": f"{ticker}: SLA at risk, predicted hour {sla['predicted_completion_hour']:.2f}",
                    "prediction": sla,
                }
            )

    if alerts and bucket:
        try:
            s3 = boto3.client("s3")
            now = datetime.utcnow()
            key = f"monitoring/predictive_alerts/{now.year}/{now.month:02d}/{now.day:02d}/{ticker}.json"
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(alerts),
                ContentType="application/json",
            )
            logger.info(f"Saved {len(alerts)} predictive alerts for {ticker} to s3://{bucket}/{key}")
        except Exception as e:
            logger.warning(f"Could not save alerts to S3: {e}")

    logger.info(f"Generated {len(alerts)} predictive alerts for {ticker}")
    return alerts


def run_predictive_monitoring(
    bucket: str,
) -> Dict[str, Any]:
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    total_alerts = 0
    by_type: Dict[str, int] = {}
    tickers_at_risk: List[str] = []

    for ticker in tickers:
        metrics: Dict[str, Any] = {}
        if bucket:
            try:
                s3 = boto3.client("s3")
                key = f"monitoring/metrics/{ticker}_latest.json"
                obj = s3.get_object(Bucket=bucket, Key=key)
                metrics = json.loads(obj["Body"].read().decode("utf-8"))
            except Exception:
                metrics = {}

        alerts = generate_predictive_alerts(ticker, metrics, bucket)
        total_alerts += len(alerts)

        if alerts:
            tickers_at_risk.append(ticker)
            for alert in alerts:
                alert_type = str(alert.get("type", "unknown"))
                by_type[alert_type] = by_type.get(alert_type, 0) + 1

    result: Dict[str, Any] = {
        "total_alerts": total_alerts,
        "by_type": by_type,
        "tickers_at_risk": tickers_at_risk,
    }
    logger.info("Predictive Monitoring Complete")
    return result


if __name__ == "__main__":
    pass
