import datetime
import json
import logging
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RECOVERY_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "retry": {
        "max_attempts": 3,
        "backoff_seconds": 60,
        "description": "Retry failed step",
    },
    "skip": {"description": "Skip failed step and continue"},
    "fallback": {"description": "Use fallback data source"},
    "checkpoint": {"description": "Resume from last checkpoint"},
    "manual": {"description": "Pause and wait for manual intervention"},
}

PIPELINE_NAMES: List[str] = ["daily_pipeline", "weekly_pipeline", "model_pipeline"]

_ACTION_MAP: Dict[str, str] = {
    "retry": "Retrying step after backoff",
    "skip": "Skipping failed step and continuing pipeline",
    "fallback": "Switching to fallback data source",
    "checkpoint": "Resuming pipeline from last checkpoint",
    "manual": "Pausing pipeline — awaiting manual intervention",
}

_CONTINUE_MAP: Dict[str, bool] = {
    "retry": True,
    "skip": True,
    "fallback": True,
    "checkpoint": True,
    "manual": False,
}


def create_checkpoint(
    pipeline_name: str, step_name: str, state: Dict[str, Any], bucket: str
) -> str:
    try:
        s3 = boto3.client("s3")
        now = datetime.datetime.utcnow()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        checkpoint_id = f"{pipeline_name}_{step_name}_{timestamp}"
        key = f"recovery/checkpoints/{pipeline_name}/{step_name}_{timestamp}.json"
        payload: Dict[str, Any] = {
            "checkpoint_id": checkpoint_id,
            "pipeline_name": pipeline_name,
            "step_name": step_name,
            "state": state,
            "created_at": now.isoformat(),
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload).encode())
        logger.info("Checkpoint created: %s", checkpoint_id)
        return checkpoint_id
    except Exception as e:
        logger.error("Failed to create checkpoint: %s", e)
        return f"{pipeline_name}_{step_name}_error"


def load_latest_checkpoint(
    pipeline_name: str, step_name: str, bucket: str
) -> Optional[Dict[str, Any]]:
    try:
        s3 = boto3.client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        prefix = f"recovery/checkpoints/{pipeline_name}/{step_name}_"
        keys: List[str] = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(str(obj["Key"]))
        if not keys:
            logger.info("No checkpoint found for %s/%s", pipeline_name, step_name)
            return None
        latest_key = sorted(keys)[-1]
        resp = s3.get_object(Bucket=bucket, Key=latest_key)
        checkpoint: Dict[str, Any] = json.loads(resp["Body"].read().decode())
        logger.info("Checkpoint loaded: %s", latest_key)
        return checkpoint
    except Exception as e:
        logger.error("Failed to load checkpoint: %s", e)
        return None


def handle_step_failure(
    pipeline_name: str,
    step_name: str,
    error: str,
    strategy: str,
    bucket: str,
) -> Dict[str, Any]:
    action_taken = _ACTION_MAP.get(strategy, "Unknown strategy applied")
    should_continue = _CONTINUE_MAP.get(strategy, False)

    try:
        s3 = boto3.client("s3")
        now = datetime.datetime.utcnow()
        key = (
            f"recovery/events/{now.year}/{now.month:02d}/{now.day:02d}/"
            f"{pipeline_name}_{step_name}_{now.strftime('%H%M%S')}.json"
        )
        payload: Dict[str, Any] = {
            "pipeline_name": pipeline_name,
            "step_name": step_name,
            "error": error,
            "strategy": strategy,
            "action_taken": action_taken,
            "should_continue": should_continue,
            "timestamp": now.isoformat(),
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload).encode())
    except Exception as e:
        logger.error("Failed to log recovery event: %s", e)

    result: Dict[str, Any] = {
        "strategy": strategy,
        "action_taken": action_taken,
        "should_continue": should_continue,
    }
    logger.info(
        "Recovery for %s/%s: strategy=%s should_continue=%s",
        pipeline_name,
        step_name,
        strategy,
        should_continue,
    )
    return result


def get_recovery_history(pipeline_name: str, bucket: str, days: int = 7) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    try:
        s3 = boto3.client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        for i in range(days):
            d = datetime.datetime.utcnow() - datetime.timedelta(days=i)
            prefix = f"recovery/events/{d.year}/{d.month:02d}/{d.day:02d}/{pipeline_name}_"
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    try:
                        resp = s3.get_object(Bucket=bucket, Key=str(obj["Key"]))
                        events.append(json.loads(resp["Body"].read().decode()))
                    except Exception:
                        continue
    except Exception as e:
        logger.error("Failed to load recovery history: %s", e)
    logger.info("Found %d recovery events for %s", len(events), pipeline_name)
    return events


def calculate_pipeline_resilience(
    recovery_history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    total = len(recovery_history)
    if total == 0:
        return {
            "auto_recovery_rate_pct": 100.0,
            "manual_interventions": 0,
            "most_common_failure": "none",
        }

    manual_count = sum(1 for e in recovery_history if str(e.get("strategy", "")) == "manual")
    auto_count = total - manual_count
    auto_recovery_rate = round((auto_count / total) * 100, 1)

    step_counts: Dict[str, int] = {}
    for e in recovery_history:
        step = str(e.get("step_name", "unknown"))
        step_counts[step] = step_counts.get(step, 0) + 1
    most_common = max(step_counts, key=lambda k: step_counts[k]) if step_counts else "none"

    result: Dict[str, Any] = {
        "auto_recovery_rate_pct": auto_recovery_rate,
        "manual_interventions": manual_count,
        "most_common_failure": most_common,
    }
    logger.info(
        "Pipeline resilience: auto_recovery=%.1f%% manual=%d",
        auto_recovery_rate,
        manual_count,
    )
    return result


def run_recovery_check(bucket: str) -> Dict[str, Any]:
    all_history: List[Dict[str, Any]] = []
    for pipeline_name in PIPELINE_NAMES:
        history = get_recovery_history(pipeline_name, bucket, days=7)
        all_history.extend(history)

    resilience = calculate_pipeline_resilience(all_history)
    result: Dict[str, Any] = {
        "pipelines_checked": len(PIPELINE_NAMES),
        "total_recovery_events": len(all_history),
        **resilience,
    }
    logger.info("Recovery Check Complete: events=%d", len(all_history))
    return result


if __name__ == "__main__":
    pass
