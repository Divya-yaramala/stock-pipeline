import json
import logging
from datetime import datetime
from typing import Optional

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PIPELINE_STEPS = [
    {
        "step_id": "S001",
        "name": "incremental_load",
        "timeout_seconds": 300,
        "retry_count": 3,
        "depends_on": [],
    },
    {
        "step_id": "S002",
        "name": "validation",
        "timeout_seconds": 60,
        "retry_count": 2,
        "depends_on": ["S001"],
    },
    {
        "step_id": "S003",
        "name": "quality_reporting",
        "timeout_seconds": 30,
        "retry_count": 1,
        "depends_on": ["S002"],
    },
    {
        "step_id": "S004",
        "name": "postgres_load",
        "timeout_seconds": 120,
        "retry_count": 3,
        "depends_on": ["S002"],
    },
    {
        "step_id": "S005",
        "name": "dbt_run",
        "timeout_seconds": 180,
        "retry_count": 2,
        "depends_on": ["S004"],
    },
    {
        "step_id": "S006",
        "name": "anomaly_detection",
        "timeout_seconds": 120,
        "retry_count": 2,
        "depends_on": ["S004"],
    },
    {
        "step_id": "S007",
        "name": "price_prediction",
        "timeout_seconds": 180,
        "retry_count": 2,
        "depends_on": ["S004"],
    },
    {
        "step_id": "S008",
        "name": "market_insights",
        "timeout_seconds": 60,
        "retry_count": 2,
        "depends_on": ["S004"],
    },
    {
        "step_id": "S009",
        "name": "snowflake_sync",
        "timeout_seconds": 120,
        "retry_count": 3,
        "depends_on": ["S005"],
    },
    {
        "step_id": "S010",
        "name": "report_generation",
        "timeout_seconds": 60,
        "retry_count": 1,
        "depends_on": ["S006", "S007", "S008"],
    },
]


def get_step_status(step_id: str, bucket: str, date: str) -> str:
    dt = datetime.strptime(date, "%Y-%m-%d")
    key = f"orchestration/{dt.strftime('%Y/%m/%d')}/{step_id}.json"
    try:
        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(response["Body"].read().decode("utf-8"))
        return data.get("status", "pending")
    except Exception:
        return "pending"


def update_step_status(
    step_id: str,
    status: str,
    bucket: str,
    date: str,
    error: Optional[str] = None,
) -> bool:
    dt = datetime.strptime(date, "%Y-%m-%d")
    key = f"orchestration/{dt.strftime('%Y/%m/%d')}/{step_id}.json"
    payload = {
        "step_id": step_id,
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if error:
        payload["error"] = error
    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Updated step %s status to %s", step_id, status)
        return True
    except Exception as exc:
        logger.error("Failed to update step %s status: %s", step_id, exc)
        return False


def get_ready_steps(bucket: str, date: str) -> list:
    ready = []
    for step in PIPELINE_STEPS:
        status = get_step_status(str(step["step_id"]), bucket, date)
        if status != "pending":
            continue
        deps = step["depends_on"]  # type: ignore[attr-defined]
        dep_statuses = [get_step_status(str(dep), bucket, date) for dep in deps]
        if all(s == "success" for s in dep_statuses):
            ready.append(step)
    logger.info("Ready steps: %s", [s["step_id"] for s in ready])
    return ready


def run_orchestration_check(bucket: str, date: str) -> dict:
    counts = {"total": len(PIPELINE_STEPS), "success": 0, "failed": 0, "pending": 0, "running": 0}
    for step in PIPELINE_STEPS:
        status = get_step_status(str(step["step_id"]), bucket, date)
        if status in counts:
            counts[status] += 1
    logger.info(
        "Pipeline progress — total: %d, success: %d, failed: %d, pending: %d, running: %d",
        counts["total"],
        counts["success"],
        counts["failed"],
        counts["pending"],
        counts["running"],
    )
    return counts


def reset_failed_steps(bucket: str, date: str) -> int:
    reset_count = 0
    for step in PIPELINE_STEPS:
        status = get_step_status(str(step["step_id"]), bucket, date)
        if status == "failed":
            update_step_status(str(step["step_id"]), "pending", bucket, date)
            reset_count += 1
    logger.info("Reset %d failed steps to pending", reset_count)
    return reset_count


if __name__ == "__main__":
    pass
