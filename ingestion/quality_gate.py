import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

QUALITY_GATES: List[Dict[str, Any]] = [
    {
        "gate_id": "G001",
        "name": "freshness_gate",
        "threshold": 25.0,
        "metric": "hours_since_update",
        "operator": "<",
        "action": "block",
    },
    {
        "gate_id": "G002",
        "name": "completeness_gate",
        "threshold": 80.0,
        "metric": "completeness_pct",
        "operator": ">",
        "action": "block",
    },
    {
        "gate_id": "G003",
        "name": "quality_score_gate",
        "threshold": 75.0,
        "metric": "quality_score",
        "operator": ">",
        "action": "warn",
    },
    {
        "gate_id": "G004",
        "name": "anomaly_rate_gate",
        "threshold": 30.0,
        "metric": "anomaly_rate_pct",
        "operator": "<",
        "action": "warn",
    },
    {
        "gate_id": "G005",
        "name": "prediction_accuracy_gate",
        "threshold": 60.0,
        "metric": "prediction_accuracy_pct",
        "operator": ">",
        "action": "block",
    },
]


def evaluate_gate(gate: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    gate_id = str(gate["gate_id"])
    metric_key = str(gate["metric"])
    threshold = float(str(gate["threshold"]))
    operator = str(gate["operator"])
    action = str(gate["action"])

    metric_value = float(str(metrics.get(metric_key, 0.0)))

    if operator == ">":
        passed = metric_value > threshold
    elif operator == "<":
        passed = metric_value < threshold
    elif operator == ">=":
        passed = metric_value >= threshold
    elif operator == "<=":
        passed = metric_value <= threshold
    else:
        passed = False

    result: Dict[str, Any] = {
        "gate_id": gate_id,
        "name": str(gate["name"]),
        "passed": passed,
        "action": action,
        "metric_value": metric_value,
        "threshold": threshold,
        "operator": operator,
    }
    status = "PASS" if passed else "FAIL"
    logger.info(
        "Gate %s (%s): %s — %s=%.2f %s %.2f",
        gate_id,
        action,
        status,
        metric_key,
        metric_value,
        operator,
        threshold,
    )
    return result


def run_quality_gates(metrics: Dict[str, Any], ticker: str) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = [evaluate_gate(g, metrics) for g in QUALITY_GATES]

    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    blocked = any(not r["passed"] and r["action"] == "block" for r in results)
    warnings = [r["gate_id"] for r in results if not r["passed"] and r["action"] == "warn"]

    summary: Dict[str, Any] = {
        "ticker": ticker,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "warnings": warnings,
        "gate_results": results,
    }
    status = "BLOCKED" if blocked else "OK"
    logger.info("Gate summary for %s: %s — %d/%d passed", ticker, status, passed, len(results))
    return summary


def save_gate_results(
    results: Dict[str, Any],
    ticker: str,
    bucket: str,
    date: str,
) -> bool:
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        key = f"quality_gates/{dt.year}/{dt.month:02d}/{dt.day:02d}/{ticker}.json"
        s3 = boto3.client("s3")
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(results))
        logger.info("Saved gate results to s3://%s/%s", bucket, key)
        return True
    except Exception as e:
        logger.error("Failed to save gate results: %s", e)
        return False


def get_gate_history(
    ticker: str,
    bucket: str,
    days: int = 7,
) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3")
    history: List[Dict[str, Any]] = []
    today = datetime.utcnow()
    for i in range(days):
        dt = today - timedelta(days=i)
        key = f"quality_gates/{dt.year}/{dt.month:02d}/{dt.day:02d}/{ticker}.json"
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            record = json.loads(obj["Body"].read().decode("utf-8"))
            history.append(record)
        except Exception:
            pass
    logger.info("Loaded %d days of gate history for %s", len(history), ticker)
    return history


def run_pipeline_gate_check(
    ticker: str,
    metrics: Dict[str, Any],
    bucket: str,
) -> bool:
    results = run_quality_gates(metrics, ticker)
    date = datetime.utcnow().strftime("%Y-%m-%d")
    save_gate_results(results, ticker, bucket, date)

    can_proceed = not results["blocked"]
    status = "PASS" if can_proceed else "BLOCK"
    logger.info("Gate Check: %s for %s", status, ticker)
    return can_proceed


if __name__ == "__main__":
    pass
