import json
import logging
import os
from datetime import datetime

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def record_pipeline_run(
    step: str,
    ticker: str,
    status: str,
    duration_seconds: float,
    bucket: str,
) -> bool:
    """Save per-step run metrics to S3 at monitoring/YYYY/MM/DD/step/ticker.json."""
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        date = datetime.now().strftime("%Y/%m/%d")
        key = f"monitoring/{date}/{step}/{ticker}.json"
        record = {
            "step": step,
            "ticker": ticker,
            "status": status,
            "duration_seconds": duration_seconds,
            "recorded_at": datetime.now().isoformat(),
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(record))
        logger.info("Monitoring record saved to s3://%s/%s", bucket, key)
        return True
    except Exception as e:
        logger.error("Failed to record pipeline run for %s/%s: %s", step, ticker, e)
        return False


def get_pipeline_metrics(bucket: str, date: str) -> list:
    """List and download all monitoring records for the given date."""
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        prefix = f"monitoring/{date}/"
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        contents = response.get("Contents", [])
        metrics = []
        for obj in contents:
            if "/reports/" in obj["Key"]:
                continue
            try:
                body = s3.get_object(Bucket=bucket, Key=obj["Key"])
                record = json.loads(body["Body"].read().decode("utf-8"))
                metrics.append(record)
            except Exception as e:
                logger.error("Failed to read monitoring record %s: %s", obj["Key"], e)

        success_count = sum(1 for m in metrics if m.get("status") == "success")
        failure_count = len(metrics) - success_count
        logger.info(
            "Pipeline metrics — total: %d, success: %d, failed: %d",
            len(metrics),
            success_count,
            failure_count,
        )
        return metrics
    except Exception as e:
        logger.error("Failed to list pipeline metrics: %s", e)
        return []


def generate_daily_report(bucket: str, date: str) -> dict:
    """Calculate daily pipeline statistics and return a summary report dict."""
    metrics = get_pipeline_metrics(bucket, date)

    total_runs = len(metrics)
    successful_runs = sum(1 for m in metrics if m.get("status") == "success")
    failed_runs = total_runs - successful_runs
    success_rate_pct = round((successful_runs / total_runs * 100) if total_runs > 0 else 0.0, 2)

    durations_by_step: dict = {}
    for m in metrics:
        step = m.get("step", "unknown")
        dur = m.get("duration_seconds", 0.0)
        durations_by_step.setdefault(step, []).append(dur)

    avg_by_step = {s: sum(v) / len(v) for s, v in durations_by_step.items()}
    avg_duration_seconds = round(
        (
            sum(m.get("duration_seconds", 0.0) for m in metrics) / total_runs
            if total_runs > 0
            else 0.0
        ),
        2,
    )
    slowest_step = max(avg_by_step, key=avg_by_step.get) if avg_by_step else None
    fastest_step = min(avg_by_step, key=avg_by_step.get) if avg_by_step else None

    report = {
        "date": date,
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "success_rate_pct": success_rate_pct,
        "avg_duration_seconds": avg_duration_seconds,
        "slowest_step": slowest_step,
        "fastest_step": fastest_step,
    }
    logger.info("Daily report: %s", json.dumps(report, indent=2))
    return report


def run_monitoring_report() -> None:
    """Generate daily report, log it, and save to S3 at monitoring/reports/YYYY/MM/DD/daily_report.json."""
    bucket = os.environ.get("AWS_BUCKET_NAME", "")
    date = datetime.now().strftime("%Y/%m/%d")

    report = generate_daily_report(bucket, date)
    logger.info(
        "Monitoring summary — total: %d, success: %d, failed: %d, success_rate: %.1f%%",
        report["total_runs"],
        report["successful_runs"],
        report["failed_runs"],
        report["success_rate_pct"],
    )

    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        key = f"monitoring/reports/{date}/daily_report.json"
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(report))
        logger.info("Daily report saved to s3://%s/%s", bucket, key)
    except Exception as e:
        logger.error("Failed to save daily report: %s", e)


if __name__ == "__main__":
    run_monitoring_report()
