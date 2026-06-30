import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def check_retraining_schedule(
    model_name: str,
    bucket: str,
    max_days_since_training: int = 30,
) -> Dict[str, Any]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    key = f"models/registry/{model_name}.json"

    last_date: Optional[str] = None
    days_since = 0

    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(response["Body"].read().decode("utf-8"))
        last_date = str(data["last_trained_date"])
        last_dt = datetime.strptime(last_date, "%Y-%m-%d")
        days_since = int((datetime.now() - last_dt).days)
    except Exception as e:
        logger.warning("Could not load model registry for %s: %s", model_name, e)

    schedule_triggered = days_since > max_days_since_training

    result: Dict[str, Any] = {
        "model_name": model_name,
        "days_since_training": days_since,
        "schedule_triggered": schedule_triggered,
    }
    logger.info(
        "Schedule check for %s: %d days since training triggered=%s",
        model_name,
        days_since,
        schedule_triggered,
    )
    _ = last_date  # captured for logging if needed
    return result


def create_retraining_job(ticker: str, reason: str, bucket: str) -> str:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    today = datetime.now().strftime("%Y/%m/%d")
    job_id = f"models/retraining_jobs/{today}/{ticker}_{timestamp}.json"

    job: Dict[str, Any] = {
        "ticker": ticker,
        "reason": reason,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }

    s3.put_object(Bucket=bucket, Key=job_id, Body=json.dumps(job))
    logger.info("Created retraining job %s for %s: %s", job_id, ticker, reason)
    return job_id


def get_pending_retraining_jobs(bucket: str) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    prefix = "models/retraining_jobs/"

    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    objects = response.get("Contents", [])

    pending: List[Dict[str, Any]] = []
    for obj in objects:
        key = str(obj["Key"])
        try:
            job_response = s3.get_object(Bucket=bucket, Key=key)
            job: Dict[str, Any] = json.loads(job_response["Body"].read().decode("utf-8"))
            if str(job.get("status", "")) == "pending":
                job["job_id"] = key
                pending.append(job)
        except Exception as e:
            logger.warning("Could not load job %s: %s", key, e)

    logger.info("Found %d pending retraining jobs", len(pending))
    return pending


def mark_job_complete(job_id: str, bucket: str, success: bool) -> bool:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    try:
        response = s3.get_object(Bucket=bucket, Key=job_id)
        job: Dict[str, Any] = json.loads(response["Body"].read().decode("utf-8"))
        job["status"] = "completed" if success else "failed"
        job["completed_at"] = datetime.now().isoformat()
        s3.put_object(Bucket=bucket, Key=job_id, Body=json.dumps(job))
        logger.info("Marked job %s as %s", job_id, str(job["status"]))
        return True
    except Exception as e:
        logger.error("Failed to update job %s: %s", job_id, e)
        return False


def run_retraining_check(tickers: List[str], bucket: str) -> Dict[str, Any]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    jobs_created = 0
    tickers_flagged: List[str] = []

    for ticker in tickers:
        needs_retrain = False
        reason: Optional[str] = None

        drift_key = f"models/drift/{datetime.now().strftime('%Y/%m/%d')}/{ticker}.json"
        try:
            drift_response = s3.get_object(Bucket=bucket, Key=drift_key)
            drift_report = json.loads(drift_response["Body"].read().decode("utf-8"))
            if drift_report.get("retrain_needed"):
                needs_retrain = True
                reason = "drift_detected"
        except Exception:
            pass

        schedule = check_retraining_schedule(ticker, bucket)
        if schedule["schedule_triggered"]:
            needs_retrain = True
            reason = reason or "schedule_triggered"

        if needs_retrain:
            try:
                create_retraining_job(ticker, str(reason), bucket)
                jobs_created += 1
                tickers_flagged.append(ticker)
            except Exception as e:
                logger.error("Failed to create job for %s: %s", ticker, e)

    result: Dict[str, Any] = {
        "jobs_created": jobs_created,
        "tickers_flagged": tickers_flagged,
    }
    logger.info("Retraining check complete: %d jobs created", jobs_created)
    return result


if __name__ == "__main__":
    pass
