import datetime
import json
import logging
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTOMATED_WORKFLOWS: List[Dict[str, Any]] = [
    {
        "workflow_id": "AW001",
        "name": "daily_market_data_refresh",
        "schedule": "0 6 * * 1-5",
        "priority": 1,
        "steps": [
            "fetch_stocks",
            "validate",
            "anomaly_detect",
            "predict",
            "insights",
            "snowflake_sync",
        ],
    },
    {
        "workflow_id": "AW002",
        "name": "weekly_model_evaluation",
        "schedule": "0 8 * * 1",
        "priority": 2,
        "steps": ["load_actuals", "calculate_accuracy", "check_drift", "update_registry"],
    },
    {
        "workflow_id": "AW003",
        "name": "monthly_compliance_report",
        "schedule": "0 9 1 * *",
        "priority": 3,
        "steps": ["run_compliance", "generate_certificates", "send_report"],
    },
    {
        "workflow_id": "AW004",
        "name": "continuous_quality_monitor",
        "schedule": "*/15 * * * *",
        "priority": 1,
        "steps": ["check_freshness", "check_quality_gates", "send_alerts"],
    },
    {
        "workflow_id": "AW005",
        "name": "ad_hoc_backfill",
        "schedule": "manual",
        "priority": 2,
        "steps": ["detect_gaps", "backfill_data", "validate_backfill"],
    },
]


def register_workflow(workflow: Dict[str, Any], bucket: str) -> bool:
    try:
        s3 = boto3.client("s3")
        workflow_id = str(workflow["workflow_id"])
        key = f"automation/workflows/{workflow_id}.json"
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(workflow).encode())
        logger.info("Workflow registered: %s", workflow_id)
        return True
    except Exception as e:
        logger.error("Failed to register workflow: %s", e)
        return False


def trigger_workflow(workflow_id: str, trigger_reason: str, bucket: str) -> str:
    try:
        s3 = boto3.client("s3")
        now = datetime.datetime.utcnow()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        execution_id = f"{workflow_id}_{timestamp}"
        key = (
            f"automation/executions/{now.year}/{now.month:02d}/{now.day:02d}/"
            f"{execution_id}.json"
        )
        payload: Dict[str, Any] = {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "trigger_reason": trigger_reason,
            "status": "pending",
            "started_at": now.isoformat(),
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload).encode())
        logger.info("Workflow triggered: %s (execution_id=%s)", workflow_id, execution_id)
        return execution_id
    except Exception as e:
        logger.error("Failed to trigger workflow: %s", e)
        return f"{workflow_id}_error"


def update_workflow_status(
    execution_id: str, status: str, step: Optional[str], bucket: str
) -> bool:
    try:
        s3 = boto3.client("s3")
        status_key = f"automation/status/{execution_id}.json"
        try:
            resp = s3.get_object(Bucket=bucket, Key=status_key)
            record: Dict[str, Any] = json.loads(resp["Body"].read().decode())
        except Exception:
            record = {"execution_id": execution_id}
        record["status"] = status
        record["current_step"] = step
        record["updated_at"] = datetime.datetime.utcnow().isoformat()
        s3.put_object(Bucket=bucket, Key=status_key, Body=json.dumps(record).encode())
        logger.info("Workflow %s status updated to %s", execution_id, status)
        return True
    except Exception as e:
        logger.error("Failed to update status: %s", e)
        return False


def get_workflow_execution_history(
    workflow_id: str, bucket: str, days: int = 7
) -> List[Dict[str, Any]]:
    executions: List[Dict[str, Any]] = []
    try:
        s3 = boto3.client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        for i in range(days):
            d = datetime.datetime.utcnow() - datetime.timedelta(days=i)
            prefix = f"automation/executions/{d.year}/{d.month:02d}/{d.day:02d}/{workflow_id}_"
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    try:
                        resp = s3.get_object(Bucket=bucket, Key=str(obj["Key"]))
                        executions.append(json.loads(resp["Body"].read().decode()))
                    except Exception:
                        continue
    except Exception as e:
        logger.error("Failed to load execution history: %s", e)
    logger.info("Found %d executions for workflow %s", len(executions), workflow_id)
    return executions


def calculate_workflow_reliability(executions: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(executions)
    if total == 0:
        return {"success_rate_pct": 100.0, "avg_duration_minutes": 0.0, "failure_count": 0}

    completed = sum(1 for e in executions if str(e.get("status", "")) == "completed")
    failed = sum(1 for e in executions if str(e.get("status", "")) == "failed")
    success_rate = round((completed / total) * 100, 1)

    durations: List[float] = []
    for e in executions:
        try:
            started = datetime.datetime.fromisoformat(str(e["started_at"]))
            finished = datetime.datetime.fromisoformat(str(e["completed_at"]))
            durations.append((finished - started).total_seconds() / 60)
        except Exception:
            continue
    avg_duration = round(sum(durations) / len(durations), 2) if durations else 0.0

    result: Dict[str, Any] = {
        "success_rate_pct": success_rate,
        "avg_duration_minutes": avg_duration,
        "failure_count": failed,
    }
    logger.info("Reliability: success_rate=%.1f%% failures=%d", success_rate, failed)
    return result


def run_automation_check(bucket: str) -> Dict[str, Any]:
    registered = 0
    for workflow in AUTOMATED_WORKFLOWS:
        if register_workflow(workflow, bucket):
            registered += 1

    recent_executions = 0
    for workflow in AUTOMATED_WORKFLOWS:
        history = get_workflow_execution_history(str(workflow["workflow_id"]), bucket, days=1)
        recent_executions += len(history)

    result: Dict[str, Any] = {
        "workflows_registered": registered,
        "recent_executions": recent_executions,
    }
    logger.info(
        "Automation Check Complete: registered=%d executions=%d",
        registered,
        recent_executions,
    )
    return result


if __name__ == "__main__":
    pass
