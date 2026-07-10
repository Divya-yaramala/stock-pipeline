import json
import logging
from datetime import datetime
from typing import Any, Dict, List

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def get_pipeline_summary(bucket: str, date: str) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    date_path = date.replace("-", "/")
    key = f"monitoring/pipeline/{date_path}/summary.json"
    defaults: Dict[str, Any] = {
        "date": date,
        "total_tickers": len(TICKERS),
        "successful_tickers": 0,
        "failed_tickers": 0,
        "avg_quality_score": 0.0,
        "total_anomalies": 0,
        "total_predictions": 0,
        "pipeline_duration_minutes": 0.0,
    }
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(obj["Body"].read().decode("utf-8"))
        summary: Dict[str, Any] = {**defaults, **data, "date": date}
    except Exception:
        summary = defaults
    logger.info(
        "Pipeline summary for %s: %d/%d tickers successful",
        date,
        int(str(summary["successful_tickers"])),
        int(str(summary["total_tickers"])),
    )
    return summary


def get_ticker_status(bucket: str, date: str) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    date_path = date.replace("-", "/")
    status: Dict[str, Any] = {}
    for ticker in TICKERS:
        key = f"monitoring/tickers/{date_path}/{ticker}.json"
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            data = json.loads(obj["Body"].read().decode("utf-8"))
            status[ticker] = {
                "status": str(data.get("status", "unknown")),
                "quality_score": float(str(data.get("quality_score", 0.0))),
                "anomalies": int(str(data.get("anomalies", 0))),
            }
        except Exception:
            status[ticker] = {"status": "unknown", "quality_score": 0.0, "anomalies": 0}
    logger.info("Ticker status loaded for %d tickers on %s", len(status), date)
    return status


def get_system_health(bucket: str) -> Dict[str, Any]:
    issues: List[str] = []
    score = 100.0

    try:
        from ingestion.resource_manager import run_resource_check

        resource = run_resource_check(bucket)
        if not resource.get("healthy", True):
            issues.append("resource_constraint")
            score -= 20.0
    except Exception:
        pass

    try:
        from datetime import date as _date

        from ingestion.sla_monitor import check_all_slas

        today = _date.today().isoformat()
        sla = check_all_slas(bucket, today)
        if float(str(sla.get("compliance_pct", 100.0))) < 80.0:
            issues.append("sla_violation")
            score -= 20.0
    except Exception:
        pass

    if score >= 80.0:
        overall = "healthy"
    elif score >= 60.0:
        overall = "warning"
    else:
        overall = "critical"

    result: Dict[str, Any] = {
        "overall_health": overall,
        "score": round(score, 1),
        "issues": issues,
    }
    logger.info("System health: %s (score=%.1f)", overall, score)
    return result


def generate_health_html(
    summary: Dict[str, Any],
    ticker_status: Dict[str, Any],
    system_health: Dict[str, Any],
) -> str:
    date = str(summary.get("date", ""))
    total = int(str(summary.get("total_tickers", 0)))
    successful = int(str(summary.get("successful_tickers", 0)))
    failed = int(str(summary.get("failed_tickers", 0)))
    avg_quality = float(str(summary.get("avg_quality_score", 0.0)))
    total_anomalies = int(str(summary.get("total_anomalies", 0)))
    total_predictions = int(str(summary.get("total_predictions", 0)))
    duration = float(str(summary.get("pipeline_duration_minutes", 0.0)))
    overall_health = str(system_health.get("overall_health", "unknown"))
    health_score = float(str(system_health.get("score", 0.0)))

    health_color = {"healthy": "#28a745", "warning": "#ffc107", "critical": "#dc3545"}.get(
        overall_health, "#6c757d"
    )

    ticker_rows = ""
    for ticker, info in ticker_status.items():
        t_status = str(info.get("status", "unknown"))
        t_quality = float(str(info.get("quality_score", 0.0)))
        t_anomalies = int(str(info.get("anomalies", 0)))
        row_color = (
            "#d4edda"
            if t_status == "success"
            else (
                "#fff3cd"
                if t_status == "warning"
                else "#f8d7da" if t_status == "failed" else "#f8f9fa"
            )
        )
        ticker_rows += (
            f'<tr style="background:{row_color}">'
            f"<td>{ticker}</td><td>{t_status}</td>"
            f"<td>{t_quality:.1f}%</td><td>{t_anomalies}</td></tr>\n"
        )

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Stock Pipeline Health Dashboard - {date}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
    h1 {{ color: #333; }}
    h2 {{ color: #555; border-bottom: 1px solid #ddd; padding-bottom: 4px; }}
    .kpi-grid {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }}
    .kpi {{ background: white; border-radius: 8px; padding: 16px; min-width: 140px;
             box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }}
    .kpi-value {{ font-size: 2em; font-weight: bold; color: #333; }}
    .kpi-label {{ font-size: 0.85em; color: #888; margin-top: 4px; }}
    table {{ border-collapse: collapse; width: 100%; background: white; border-radius: 8px;
             box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #eee; }}
    th {{ background: #f0f0f0; font-weight: bold; }}
    .health-badge {{ display: inline-block; padding: 6px 14px; border-radius: 16px;
                     color: white; font-weight: bold; background: {health_color}; }}
  </style>
</head>
<body>
  <h1>Stock Pipeline Health Dashboard - {date}</h1>

  <h2>Pipeline Summary</h2>
  <div class="kpi-grid">
    <div class="kpi"><div class="kpi-value">{total}</div>
      <div class="kpi-label">Total Tickers</div></div>
    <div class="kpi"><div class="kpi-value">{successful}</div>
      <div class="kpi-label">Successful</div></div>
    <div class="kpi"><div class="kpi-value">{failed}</div>
      <div class="kpi-label">Failed</div></div>
    <div class="kpi"><div class="kpi-value">{avg_quality:.1f}%</div>
      <div class="kpi-label">Avg Quality</div></div>
    <div class="kpi"><div class="kpi-value">{total_anomalies}</div>
      <div class="kpi-label">Anomalies</div></div>
    <div class="kpi"><div class="kpi-value">{total_predictions}</div>
      <div class="kpi-label">Predictions</div></div>
    <div class="kpi"><div class="kpi-value">{duration:.1f}m</div>
      <div class="kpi-label">Duration</div></div>
  </div>

  <h2>Ticker Status</h2>
  <table>
    <tr><th>Ticker</th><th>Status</th><th>Quality Score</th><th>Anomalies</th></tr>
    {ticker_rows}
  </table>

  <h2>System Health</h2>
  <p>
    <span class="health-badge">{overall_health.upper()}</span>
    &nbsp; Score: {health_score:.1f} / 100
  </p>
</body>
</html>"""
    return html


def save_health_dashboard(html: str, bucket: str, date: str) -> str:
    dt = datetime.strptime(date, "%Y-%m-%d")
    key = f"reports/health_dashboard/{dt.year}/{dt.month:02d}/{dt.day:02d}/dashboard.html"
    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=html.encode("utf-8"),
            ContentType="text/html",
        )
        url = f"s3://{bucket}/{key}"
        logger.info("Health dashboard saved to %s", url)
        return url
    except Exception as e:
        logger.error("Failed to save health dashboard: %s", e)
        return ""


def run_health_dashboard_update(bucket: str) -> str:
    date = datetime.utcnow().strftime("%Y-%m-%d")
    summary = get_pipeline_summary(bucket, date)
    ticker_status = get_ticker_status(bucket, date)
    system_health = get_system_health(bucket)
    html = generate_health_html(summary, ticker_status, system_health)
    url = save_health_dashboard(html, bucket, date)
    logger.info("Health Dashboard Updated: %s", url)
    return url


if __name__ == "__main__":
    pass
