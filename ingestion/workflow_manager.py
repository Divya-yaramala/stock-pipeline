import boto3
import json
import os
import logging
import datetime
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

WORKFLOWS = [
    {
        "workflow_id": "W001",
        "name": "daily_market_pipeline",
        "schedule": "0 6 * * 1-5",
        "description": "Main daily pipeline weekdays at 6 AM",
    },
    {
        "workflow_id": "W002",
        "name": "weekly_report",
        "schedule": "0 8 * * 1",
        "description": "Weekly report every Monday at 8 AM",
    },
    {
        "workflow_id": "W003",
        "name": "monthly_backfill",
        "schedule": "0 2 1 * *",
        "description": "Monthly backfill on 1st at 2 AM",
    },
    {
        "workflow_id": "W004",
        "name": "hourly_health_check",
        "schedule": "0 * * * *",
        "description": "Hourly health check",
    },
    {
        "workflow_id": "W005",
        "name": "real_time_streaming",
        "schedule": "continuous",
        "description": "Continuous Kafka streaming",
    },
]


def parse_cron_schedule(cron_expr: str) -> dict:
    if cron_expr == "continuous":
        return {"schedule": "continuous"}
    parts = cron_expr.split()
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "weekday": parts[4],
    }


def is_workflow_due(workflow: dict, current_time: datetime.datetime) -> bool:
    schedule = workflow.get("schedule", "")
    if schedule == "continuous":
        logger.info("Workflow %s is continuous — always due", workflow.get("workflow_id"))
        return True

    parsed = parse_cron_schedule(schedule)
    hour_match = parsed["hour"] == "*" or str(current_time.hour) == parsed["hour"]
    minute_match = parsed["minute"] == "*" or str(current_time.minute) == parsed["minute"]

    weekday_field = parsed["weekday"]
    if "-" in weekday_field:
        start, end = weekday_field.split("-")
        weekday_match = int(start) <= current_time.isoweekday() <= int(end)
    elif weekday_field == "*":
        weekday_match = True
    else:
        weekday_match = str(current_time.isoweekday()) == weekday_field

    day_match = parsed["day"] == "*" or str(current_time.day) == parsed["day"]
    month_match = parsed["month"] == "*" or str(current_time.month) == parsed["month"]

    due = hour_match and minute_match and weekday_match and day_match and month_match
    logger.info(
        "Workflow %s due check: %s",
        workflow.get("workflow_id"),
        due,
    )
    return due


def trigger_workflow(workflow_id: str, bucket: str) -> bool:
    now = datetime.datetime.utcnow()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    key = f"workflows/triggers/{now.year}/{now.month:02d}/{now.day:02d}/{workflow_id}_{timestamp}.json"
    record = {
        "workflow_id": workflow_id,
        "triggered_at": now.isoformat(),
        "status": "triggered",
    }
    try:
        s3 = boto3.client("s3")
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(record))
        logger.info("Workflow %s triggered — saved to s3://%s/%s", workflow_id, bucket, key)
        return True
    except Exception as e:
        logger.error("Failed to trigger workflow %s: %s", workflow_id, e)
        return False


def get_workflow_history(workflow_id: str, bucket: str, days: int = 7) -> list:
    records = []
    s3 = boto3.client("s3")
    now = datetime.datetime.utcnow()
    for i in range(days):
        day = now - datetime.timedelta(days=i)
        prefix = f"workflows/triggers/{day.year}/{day.month:02d}/{day.day:02d}/{workflow_id}_"
        try:
            response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            for obj in response.get("Contents", []):
                body = s3.get_object(Bucket=bucket, Key=obj["Key"])["Body"].read()
                records.append(json.loads(body))
        except Exception as e:
            logger.warning("Could not load history for %s on %s: %s", workflow_id, day.date(), e)
    logger.info("Found %d trigger records for workflow %s", len(records), workflow_id)
    return records


def get_due_workflows(current_time: datetime.datetime) -> list:
    due = [wf for wf in WORKFLOWS if is_workflow_due(wf, current_time)]
    logger.info("%d workflow(s) due at %s", len(due), current_time.isoformat())
    return due


def run_workflow_check(bucket: str) -> dict:
    current_time = datetime.datetime.utcnow()
    due = get_due_workflows(current_time)
    triggered_workflows = []
    for wf in due:
        success = trigger_workflow(wf["workflow_id"], bucket)
        if success:
            triggered_workflows.append(wf["workflow_id"])
    return {"triggered": len(triggered_workflows), "workflows": triggered_workflows}


if __name__ == "__main__":
    pass
