import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REMEDIATION_ACTIONS: Dict[str, str] = {
    "stale_data": "trigger_backfill",
    "missing_files": "rerun_ingestion",
    "low_quality": "rerun_validation",
    "high_anomaly_rate": "rerun_anomaly_detection",
    "prediction_failure": "use_fallback_model",
}


def detect_issue(metrics: Dict[str, Any], ticker: str) -> Optional[str]:
    hours_since_update = float(str(metrics.get("hours_since_update", 0.0)))
    completeness_pct = float(str(metrics.get("completeness_pct", 100.0)))
    quality_score = float(str(metrics.get("quality_score", 100.0)))
    anomaly_rate_pct = float(str(metrics.get("anomaly_rate_pct", 0.0)))
    prediction_accuracy_pct = float(str(metrics.get("prediction_accuracy_pct", 100.0)))

    if hours_since_update >= 25.0:
        logger.info("Issue detected for %s: stale_data (hours=%.1f)", ticker, hours_since_update)
        return "stale_data"
    if completeness_pct < 50.0:
        logger.info("Issue detected for %s: missing_files (completeness=%.1f%%)", ticker,
                    completeness_pct)
        return "missing_files"
    if quality_score < 60.0:
        logger.info("Issue detected for %s: low_quality (score=%.1f)", ticker, quality_score)
        return "low_quality"
    if anomaly_rate_pct >= 50.0:
        logger.info("Issue detected for %s: high_anomaly_rate (rate=%.1f%%)", ticker,
                    anomaly_rate_pct)
        return "high_anomaly_rate"
    if prediction_accuracy_pct < 50.0:
        logger.info("Issue detected for %s: prediction_failure (accuracy=%.1f%%)", ticker,
                    prediction_accuracy_pct)
        return "prediction_failure"

    logger.info("No issue detected for %s", ticker)
    return None


def trigger_remediation(issue: str, ticker: str, bucket: str) -> Dict[str, Any]:
    action = str(REMEDIATION_ACTIONS.get(issue, "unknown"))
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    now = datetime.utcnow()
    key = (
        f"remediation/{now.year}/{now.month:02d}/{now.day:02d}/"
        f"{ticker}_{issue}_{timestamp}.json"
    )
    record: Dict[str, Any] = {
        "issue": issue,
        "action": action,
        "ticker": ticker,
        "status": "triggered",
        "created_at": datetime.utcnow().isoformat(),
    }
    try:
        s3 = boto3.client("s3")
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(record))
        logger.info("Auto Remediation: %s triggered for %s (issue=%s)", action, ticker, issue)
    except Exception as e:
        logger.error("Failed to save remediation record: %s", e)
    return record


def get_remediation_history(
    ticker: str,
    bucket: str,
    days: int = 7,
) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3")
    history: List[Dict[str, Any]] = []
    today = datetime.utcnow()
    for i in range(days):
        dt = today - timedelta(days=i)
        prefix = f"remediation/{dt.year}/{dt.month:02d}/{dt.day:02d}/{ticker}_"
        try:
            response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            for obj in response.get("Contents", []):
                data = s3.get_object(Bucket=bucket, Key=str(obj["Key"]))
                record = json.loads(data["Body"].read().decode("utf-8"))
                history.append(record)
        except Exception:
            pass
    logger.info("Loaded %d remediation records for %s", len(history), ticker)
    return history


def run_auto_remediation(
    ticker: str,
    metrics: Dict[str, Any],
    bucket: str,
) -> Optional[Dict[str, Any]]:
    issue = detect_issue(metrics, ticker)
    if issue is None:
        return None
    record = trigger_remediation(issue, ticker, bucket)
    return record


if __name__ == "__main__":
    pass
