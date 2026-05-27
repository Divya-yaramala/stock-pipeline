import json
import logging
import os
from datetime import datetime

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def record_sla_metric(
    step: str,
    expected_duration_seconds: float,
    actual_duration_seconds: float,
    bucket: str,
) -> bool:
    """Save an SLA metric record to S3 at monitoring/sla/YYYY/MM/DD/step_timestamp.json."""
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date = datetime.now().strftime("%Y/%m/%d")
        key = f"monitoring/sla/{date}/{step}_{timestamp}.json"
        sla_met = actual_duration_seconds <= expected_duration_seconds
        record = {
            "step": step,
            "expected_duration_seconds": expected_duration_seconds,
            "actual_duration_seconds": actual_duration_seconds,
            "sla_met": sla_met,
            "recorded_at": datetime.now().isoformat(),
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(record))
        logger.info(
            "SLA metric saved — %s: %.1fs actual vs %.1fs expected (%s)",
            step,
            actual_duration_seconds,
            expected_duration_seconds,
            "MET" if sla_met else "MISSED",
        )
        return True
    except Exception as e:
        logger.error("Failed to record SLA metric for %s: %s", step, e)
        return False


def get_sla_thresholds() -> dict:
    """Return hardcoded per-step SLA thresholds in seconds."""
    return {
        "fetch": 30,
        "validation": 10,
        "anomaly": 60,
        "prediction": 120,
        "insights": 45,
        "snowflake_sync": 30,
        "monitoring": 15,
    }


def check_all_slas(bucket: str, date: str) -> dict:
    """Load today's SLA records from S3 and compare each step against its threshold."""
    thresholds = get_sla_thresholds()
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        prefix = f"monitoring/sla/{date}/"
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        contents = response.get("Contents", [])

        latest: dict = {}
        for obj in contents:
            try:
                body = s3.get_object(Bucket=bucket, Key=obj["Key"])
                record = json.loads(body["Body"].read().decode("utf-8"))
                step = record.get("step", "")
                recorded_at = record.get("recorded_at", "")
                if step not in latest or recorded_at > latest[step].get("recorded_at", ""):
                    latest[step] = record
            except Exception as e:
                logger.error("Failed to read SLA record %s: %s", obj["Key"], e)

        results = {}
        for step, record in latest.items():
            actual = record.get("actual_duration_seconds", 0.0)
            threshold = thresholds.get(step, float("inf"))
            results[step] = {
                "met": actual <= threshold,
                "actual": actual,
                "threshold": threshold,
            }
        return results
    except Exception as e:
        logger.error("Failed to check SLAs: %s", e)
        return {}


def generate_sla_report(bucket: str, date: str) -> None:
    """Log SLA table, alert on misses, and save report to S3."""
    from ingestion import slack_alerter

    results = check_all_slas(bucket, date)

    logger.info("%-16s | %-10s | %-8s | %s", "Step", "Threshold", "Actual", "Met")
    logger.info("-" * 52)
    missed_steps = []
    for step, data in results.items():
        icon = "✅" if data["met"] else "❌"
        logger.info(
            "%-16s | %-10s | %-8s | %s",
            step,
            f"{data['threshold']}s",
            f"{data['actual']:.1f}s",
            icon,
        )
        if not data["met"]:
            missed_steps.append(step)

    if missed_steps:
        slack_alerter.alert_pipeline_failure(
            "sla_monitor",
            "pipeline",
            f"SLA missed for steps: {', '.join(missed_steps)}",
        )

    report = {"date": date, "generated_at": datetime.now().isoformat(), "slas": results}
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        key = f"reports/sla/{date}/sla_report.json"
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(report))
        logger.info("SLA report saved to s3://%s/%s", bucket, key)
    except Exception as e:
        logger.error("Failed to save SLA report: %s", e)


if __name__ == "__main__":
    generate_sla_report(
        os.getenv("AWS_BUCKET_NAME", ""),
        datetime.now().strftime("%Y/%m/%d"),
    )
