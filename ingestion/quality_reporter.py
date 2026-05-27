from collections import Counter
import json
import logging
import os
from datetime import datetime

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def load_validation_reports(bucket: str, date: str) -> list:
    """Load all per-ticker validation reports from S3 for the given date."""
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        prefix = f"processed/validation/{date}/"
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        contents = response.get("Contents", [])
        reports = []
        for obj in contents:
            try:
                body = s3.get_object(Bucket=bucket, Key=obj["Key"])
                report = json.loads(body["Body"].read().decode("utf-8"))
                reports.append(report)
            except Exception as e:
                logger.error("Failed to load report %s: %s", obj["Key"], e)
        logger.info("Loaded %d validation reports for %s", len(reports), date)
        return reports
    except Exception as e:
        logger.error("Failed to list validation reports: %s", e)
        return []


def calculate_quality_score(reports: list) -> dict:
    """Derive overall quality metrics from a list of per-ticker validation reports."""
    total = len(reports)
    if total == 0:
        return {
            "total_tickers": 0,
            "passed_tickers": 0,
            "failed_tickers": 0,
            "quality_score_pct": 0.0,
            "failed_checks": [],
            "most_common_failure": None,
        }

    passed = sum(1 for r in reports if r.get("passed"))
    failed = total - passed
    score = round(passed / total * 100, 2)

    all_failures = []
    for report in reports:
        for check_name, check_passed in report.get("checks", {}).items():
            if not check_passed:
                all_failures.append(check_name)

    counts = Counter(all_failures)
    most_common_failure = counts.most_common(1)[0][0] if counts else None

    return {
        "total_tickers": total,
        "passed_tickers": passed,
        "failed_tickers": failed,
        "quality_score_pct": score,
        "failed_checks": list(set(all_failures)),
        "most_common_failure": most_common_failure,
    }


def generate_quality_report(bucket: str, date: str) -> dict:
    """Build and save the daily quality report; return the full report dict."""
    reports = load_validation_reports(bucket, date)
    metrics = calculate_quality_score(reports)
    report = {
        "date": date,
        "generated_at": datetime.now().isoformat(),
        **metrics,
    }
    logger.info(
        "Quality score for %s: %.1f%% (%d/%d tickers passed)",
        date,
        report["quality_score_pct"],
        report["passed_tickers"],
        report["total_tickers"],
    )
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        key = f"reports/quality/{date}/quality_report.json"
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(report))
        logger.info("Quality report saved to s3://%s/%s", bucket, key)
    except Exception as e:
        logger.error("Failed to save quality report: %s", e)
    return report


def check_quality_sla(report: dict, threshold: float = 80.0) -> bool:
    """Return True if quality_score_pct meets the threshold, False otherwise."""
    score = report.get("quality_score_pct", 0.0)
    if score >= threshold:
        logger.info("Quality SLA PASSED: %.1f%% >= %.1f%%", score, threshold)
        return True
    logger.warning("Quality SLA FAILED: %.1f%% < %.1f%%", score, threshold)
    return False


def run_quality_reporting() -> None:
    """Generate quality report, check SLA, and alert on failure."""
    from ingestion import slack_alerter

    bucket = os.environ.get("AWS_BUCKET_NAME", "")
    date = datetime.now().strftime("%Y/%m/%d")
    report = generate_quality_report(bucket, date)
    sla_ok = check_quality_sla(report)
    if not sla_ok:
        slack_alerter.alert_pipeline_failure(
            "quality_sla",
            "pipeline",
            f"Quality score {report['quality_score_pct']:.1f}% is below 80% threshold",
        )
    logger.info("Quality reporting complete — SLA %s", "PASSED" if sla_ok else "FAILED")


if __name__ == "__main__":
    run_quality_reporting()
