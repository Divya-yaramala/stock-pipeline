import datetime
import json
import logging
import time

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_schedule(name: str, cron_expr: str, pipeline_steps: list, bucket: str) -> str:
    schedule_id = f"SCH_{name}_{int(time.time())}"
    record = {
        "schedule_id": schedule_id,
        "name": name,
        "cron_expr": cron_expr,
        "pipeline_steps": pipeline_steps,
        "status": "active",
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    key = f"scheduler/schedules/{name}.json"
    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(record))
    logger.info("Schedule created: %s (id=%s)", name, schedule_id)
    return schedule_id


def get_schedule(name: str, bucket: str) -> dict:
    key = f"scheduler/schedules/{name}.json"
    try:
        s3 = boto3.client("s3")
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        return json.loads(body)
    except Exception as e:
        logger.warning("Schedule '%s' not found: %s", name, e)
        return {}


def update_schedule(name: str, updates: dict, bucket: str) -> bool:
    existing = get_schedule(name, bucket)
    if not existing:
        logger.error("Cannot update — schedule '%s' not found", name)
        return False
    existing.update(updates)
    existing["updated_at"] = datetime.datetime.utcnow().isoformat()
    key = f"scheduler/schedules/{name}.json"
    try:
        s3 = boto3.client("s3")
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(existing))
        logger.info("Schedule '%s' updated", name)
        return True
    except Exception as e:
        logger.error("Failed to update schedule '%s': %s", name, e)
        return False


def disable_schedule(name: str, bucket: str) -> bool:
    result = update_schedule(name, {"status": "disabled"}, bucket)
    if result:
        logger.info("Schedule '%s' disabled", name)
    return result


def get_next_run_time(cron_expr: str, from_time: datetime.datetime) -> datetime.datetime:
    parts = cron_expr.split()
    minute = int(parts[0]) if parts[0] != "*" else 0
    hour = int(parts[1]) if parts[1] != "*" else from_time.hour

    candidate = from_time.replace(second=0, microsecond=0, minute=minute, hour=hour)
    if candidate <= from_time:
        candidate += datetime.timedelta(hours=1 if parts[1] == "*" else 24)

    logger.info(
        "Next run for '%s' after %s is %s", cron_expr, from_time.isoformat(), candidate.isoformat()
    )
    return candidate


def run_scheduler_check(bucket: str) -> dict:
    s3 = boto3.client("s3")
    prefix = "scheduler/schedules/"
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        objects = response.get("Contents", [])
    except Exception as e:
        logger.error("Failed to list schedules: %s", e)
        return {"active": 0, "due": 0, "schedules": []}

    active = []
    due = []
    now = datetime.datetime.utcnow()

    for obj in objects:
        try:
            body = s3.get_object(Bucket=bucket, Key=obj["Key"])["Body"].read()
            schedule = json.loads(body)
            if schedule.get("status") == "active":
                active.append(schedule["name"])
                next_run = get_next_run_time(schedule["cron_expr"], now)
                if (next_run - now).total_seconds() < 60:
                    due.append(schedule["name"])
        except Exception as e:
            logger.warning("Could not load schedule from %s: %s", obj["Key"], e)

    logger.info("Scheduler check: %d active, %d due", len(active), len(due))
    return {"active": len(active), "due": len(due), "schedules": active}


if __name__ == "__main__":
    pass
