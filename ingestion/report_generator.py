import json
import logging
import os
from datetime import datetime

import boto3
from jinja2 import Template

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: Arial, sans-serif; margin: 30px; background: #f9f9f9; color: #333; }
  h1 { color: #2c3e50; }
  h2 { color: #34495e; border-bottom: 2px solid #ecf0f1; padding-bottom: 6px; margin-top: 30px; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 20px; background: #fff; }
  th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
  th { background: #2c3e50; color: #fff; }
  .good { color: #27ae60; font-weight: bold; }
  .bad { color: #e74c3c; font-weight: bold; }
</style>
</head>
<body>
<h1>Daily Pipeline Report - {{ date }}</h1>

<h2>Pipeline Summary</h2>
<table>
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Total Runs</td><td>{{ total_runs }}</td></tr>
  <tr><td>Success Rate</td>
  <td class="{{ 'good' if success_rate_pct >= 80 else 'bad' }}">{{ success_rate_pct }}%</td></tr>
</table>

<h2>Data Quality Score</h2>
<table>
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Quality Score</td>
  <td class="{{ 'good' if quality_score_pct >= 80 else 'bad' }}">{{ quality_score_pct }}%</td></tr>
  <tr><td>Passed Tickers</td><td>{{ passed_tickers }}</td></tr>
  <tr><td>Total Tickers</td><td>{{ total_tickers }}</td></tr>
</table>

<h2>SLA Compliance</h2>
<table>
  <tr><th>Step</th><th>Status</th><th>Actual (s)</th><th>Threshold (s)</th></tr>
  {% for step, data in slas.items() %}
  <tr>
    <td>{{ step }}</td>
    <td class="{{ 'good' if data.met else 'bad' }}">{{ 'MET' if data.met else 'MISSED' }}</td>
    <td>{{ "%.1f"|format(data.actual) }}</td>
    <td>{{ data.threshold }}</td>
  </tr>
  {% else %}
  <tr><td colspan="4">No SLA data available</td></tr>
  {% endfor %}
</table>

<h2>Top Anomalies Detected Today</h2>
<table>
  <tr><th>Ticker</th><th>Status</th></tr>
  {% for ticker in anomalies %}
  <tr><td>{{ ticker }}</td><td class="bad">Anomaly Detected</td></tr>
  {% else %}
  <tr><td colspan="2">No anomaly data available</td></tr>
  {% endfor %}
</table>

<h2>Predictions Summary</h2>
<table>
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Slowest Step</td><td>{{ slowest_step }}</td></tr>
  <tr><td>Fastest Step</td><td>{{ fastest_step }}</td></tr>
  <tr><td>Avg Duration (s)</td><td>{{ avg_duration_seconds }}</td></tr>
</table>
</body>
</html>"""


def load_daily_metrics(bucket: str, date: str) -> dict:
    """
    Load quality, SLA, and monitoring reports from S3 for the given date.

    Args:
        bucket: S3 bucket name.
        date: Date string in YYYY-MM-DD format.

    Returns:
        Combined dict with keys: quality, sla, monitoring.
    """
    date_path = date.replace("-", "/")
    s3 = boto3.client("s3")

    files = [
        ("quality", f"reports/quality/{date_path}/quality_report.json"),
        ("sla", f"reports/sla/{date_path}/sla_report.json"),
        ("monitoring", f"monitoring/reports/{date_path}/daily_report.json"),
    ]

    metrics = {}
    for key_name, s3_key in files:
        try:
            response = s3.get_object(Bucket=bucket, Key=s3_key)
            metrics[key_name] = json.loads(response["Body"].read().decode("utf-8"))
            logger.info("Loaded %s from s3://%s/%s", key_name, bucket, s3_key)
        except Exception as e:
            logger.warning("Could not load %s (%s): %s", key_name, s3_key, e)
            metrics[key_name] = {}

    return metrics


def generate_html_report(metrics: dict, date: str) -> str:
    """
    Render an HTML pipeline report from daily metrics.

    Args:
        metrics: Combined metrics dict from load_daily_metrics.
        date: Date string in YYYY-MM-DD format, shown in the report title.

    Returns:
        Rendered HTML string.
    """
    monitoring = metrics.get("monitoring", {})
    quality = metrics.get("quality", {})
    sla = metrics.get("sla", {})

    template = Template(_HTML_TEMPLATE)
    return template.render(
        date=date,
        total_runs=monitoring.get("total_runs", 0),
        success_rate_pct=monitoring.get("success_rate_pct", 0),
        quality_score_pct=quality.get("quality_score_pct", 0),
        passed_tickers=quality.get("passed_tickers", 0),
        total_tickers=quality.get("total_tickers", 0),
        slas=sla.get("slas", {}),
        anomalies=quality.get("failed_checks", []),
        slowest_step=monitoring.get("slowest_step", "N/A"),
        fastest_step=monitoring.get("fastest_step", "N/A"),
        avg_duration_seconds=round(monitoring.get("avg_duration_seconds", 0), 2),
    )


def save_report_to_s3(html: str, bucket: str, date: str) -> str:
    """
    Save the HTML report to S3.

    Args:
        html: Rendered HTML string.
        bucket: S3 bucket name.
        date: Date string in YYYY-MM-DD format.

    Returns:
        S3 URL string for the saved report.
    """
    date_path = date.replace("-", "/")
    key = f"reports/daily/{date_path}/pipeline_report.html"
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=html.encode("utf-8"),
        ContentType="text/html",
    )
    s3_url = f"s3://{bucket}/{key}"
    logger.info("Daily report saved to %s", s3_url)
    return s3_url


def run_report_generation() -> None:
    """Load daily metrics, render HTML report, and save to S3."""
    bucket = os.getenv("AWS_BUCKET_NAME", "")
    date = datetime.utcnow().strftime("%Y-%m-%d")
    metrics = load_daily_metrics(bucket, date)
    html = generate_html_report(metrics, date)
    save_report_to_s3(html, bucket, date)
    logger.info("Daily report generated for %s", date)


if __name__ == "__main__":
    run_report_generation()
