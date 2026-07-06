"""
Pipeline Monitoring
-------------------
Tracks execution metrics for every pipeline step including
duration, success/failure status, and timestamps. This enables:
- SLA monitoring (detect slow steps)
- Failure rate tracking per step
- Daily summary reports for ops review
"""

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
    """
    Save per-step run metrics to S3 at monitoring/YYYY/MM/DD/step/ticker.json.

    Args:
        step: Pipeline step name (e.g. 'fetch', 'anomaly').
        ticker: Stock ticker symbol.
        status: Outcome string, either 'success' or 'failure'.
        duration_seconds: Wall-clock time the step took in seconds.
        bucket: S3 bucket name.

    Returns:
        True if the record was saved successfully, False otherwise.
    """
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
    """
    List and download all monitoring records for the given date.

    Args:
        bucket: S3 bucket name.
        date: Date string in YYYY/MM/DD format.

    Returns:
        List of monitoring record dicts; excludes report objects under /reports/.
    """
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
    """
    Calculate daily pipeline statistics and return a summary report dict.

    Args:
        bucket: S3 bucket name.
        date: Date string in YYYY/MM/DD format.

    Returns:
        Dict with keys: date, total_runs, successful_runs, failed_runs,
        success_rate_pct, avg_duration_seconds, slowest_step, fastest_step.
    """
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
    slowest_step = max(avg_by_step, key=lambda x: float(avg_by_step[x])) if avg_by_step else None
    fastest_step = min(avg_by_step, key=lambda x: float(avg_by_step[x])) if avg_by_step else None

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
    """
    Generate daily report, save it to S3, and send a Slack summary alert.

    Report is saved to monitoring/reports/YYYY/MM/DD/daily_report.json.
    """
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

    from ingestion import slack_alerter

    slack_alerter.send_daily_summary(
        total_tickers=int(str(report.get("total_runs", 0))),
        anomalies_found=0,
        predictions_made=int(str(report.get("total_runs", 0))),
        avg_quality_score=float(str(report.get("success_rate_pct", 0.0))),
    )


if __name__ == "__main__":
    run_monitoring_report()
