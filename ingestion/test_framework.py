import json
import logging
import os
import time
from datetime import datetime, timedelta

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

TEST_SUITE = [
    {
        "test_id": "T001",
        "name": "data_freshness_check",
        "category": "data_quality",
        "severity": "HIGH",
    },
    {
        "test_id": "T002",
        "name": "completeness_check",
        "category": "data_quality",
        "severity": "HIGH",
    },
    {
        "test_id": "T003",
        "name": "consistency_check",
        "category": "data_quality",
        "severity": "MEDIUM",
    },
    {
        "test_id": "T004",
        "name": "anomaly_detection_check",
        "category": "ai_quality",
        "severity": "MEDIUM",
    },
    {
        "test_id": "T005",
        "name": "prediction_accuracy_check",
        "category": "ai_quality",
        "severity": "LOW",
    },
    {
        "test_id": "T006",
        "name": "sentiment_coverage_check",
        "category": "ai_quality",
        "severity": "LOW",
    },
    {
        "test_id": "T007",
        "name": "pipeline_sla_check",
        "category": "performance",
        "severity": "HIGH",
    },
    {
        "test_id": "T008",
        "name": "api_health_check",
        "category": "infrastructure",
        "severity": "HIGH",
    },
]


def run_test(test_id: str, bucket: str, date: str) -> dict:
    test_def = next((t for t in TEST_SUITE if t["test_id"] == test_id), None)
    if not test_def:
        return {
            "test_id": test_id,
            "name": "unknown",
            "status": "fail",
            "duration_ms": 0.0,
            "details": f"Test {test_id} not found in suite",
        }

    start = time.time()
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        s3 = boto3.client("s3", region_name=AWS_REGION)
        prefix = f"raw/stocks/{dt.strftime('%Y/%m/%d')}/"
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        found = len(response.get("Contents", [])) > 0
        status = "pass" if found else "fail"
        details = "Data found" if found else "No data found for date"
    except Exception as exc:
        status = "fail"
        details = str(exc)

    duration_ms = (time.time() - start) * 1000
    result = {
        "test_id": test_id,
        "name": test_def["name"],
        "status": status,
        "duration_ms": round(duration_ms, 2),
        "details": details,
    }
    logger.info("Test %s (%s): %s", test_id, test_def["name"], status)
    return result


def run_test_suite(bucket: str, date: str) -> dict:
    results = [run_test(t["test_id"], bucket, date) for t in TEST_SUITE]
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = len(results) - passed
    pass_rate = round((passed / len(results)) * 100, 1) if results else 0.0
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "pass_rate_pct": pass_rate,
        "results": results,
    }
    logger.info(
        "Test suite complete — total: %d, passed: %d, failed: %d, pass_rate: %.1f%%",
        len(results),
        passed,
        failed,
        pass_rate,
    )
    return summary


def save_test_results(results: dict, bucket: str, date: str) -> bool:
    dt = datetime.strptime(date, "%Y-%m-%d")
    key = f"testing/{dt.strftime('%Y/%m/%d')}/test_results.json"
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(results).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Test results saved to s3://%s/%s", bucket, key)
        return True
    except Exception as exc:
        logger.error("Failed to save test results: %s", exc)
        return False


def get_test_history(bucket: str, days: int = 7) -> list:
    history = []
    s3 = boto3.client("s3", region_name=AWS_REGION)
    for i in range(days):
        dt = datetime.utcnow() - timedelta(days=i)
        key = f"testing/{dt.strftime('%Y/%m/%d')}/test_results.json"
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            data = json.loads(response["Body"].read().decode("utf-8"))
            history.append(data)
        except Exception:
            pass
    logger.info("Loaded %d days of test history", len(history))
    return history


def calculate_quality_trend(history: list) -> dict:
    if not history:
        return {"trend": "stable", "avg_pass_rate": 0.0}

    rates = [h.get("pass_rate_pct", 0.0) for h in history]
    avg = round(sum(rates) / len(rates), 1)

    if len(rates) >= 2:
        first_half = sum(rates[: len(rates) // 2]) / max(len(rates) // 2, 1)
        second_half = sum(rates[len(rates) // 2 :]) / max(len(rates) - len(rates) // 2, 1)
        if second_half > first_half + 2:
            trend = "improving"
        elif second_half < first_half - 2:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "stable"

    return {"trend": trend, "avg_pass_rate": avg}


if __name__ == "__main__":
    pass
