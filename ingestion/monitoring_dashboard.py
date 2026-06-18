import json
import logging
from datetime import datetime, timedelta, timezone

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def get_pipeline_kpis(bucket: str, date: str) -> dict:
    s3 = boto3.client("s3")
    date_path = date.replace("-", "/")
    s3_key = f"monitoring/pipeline/{date_path}/summary.json"
    defaults = {
        "total_runs": 0,
        "success_rate_pct": 0.0,
        "avg_duration_seconds": 0.0,
        "quality_score_pct": 0.0,
        "anomaly_count": 0,
        "prediction_accuracy_pct": 0.0,
        "dlq_count": 0,
        "sla_met_pct": 0.0,
    }
    try:
        response = s3.get_object(Bucket=bucket, Key=s3_key)
        data = json.loads(response["Body"].read())
        kpis = {**defaults, **data}
        logger.info(
            f"KPIs loaded: success={kpis['success_rate_pct']}%, "
            f"quality={kpis['quality_score_pct']}%"
        )
        return kpis
    except Exception:
        logger.info(f"No KPI data for {date}, returning defaults")
        return defaults


def get_ticker_health(bucket: str, date: str) -> dict:
    s3 = boto3.client("s3")
    date_path = date.replace("-", "/")
    health = {}
    for ticker in TICKERS:
        s3_key = f"monitoring/tickers/{date_path}/{ticker}.json"
        try:
            response = s3.get_object(Bucket=bucket, Key=s3_key)
            data = json.loads(response["Body"].read())
            quality = float(data.get("quality_score", 0.0))
            if quality > 90:
                status = "healthy"
            elif quality > 70:
                status = "warning"
            else:
                status = "critical"
            health[ticker] = {
                "status": status,
                "last_updated": data.get("last_updated", date),
                "quality_score": quality,
            }
        except Exception:
            health[ticker] = {
                "status": "critical",
                "last_updated": date,
                "quality_score": 0.0,
            }
    healthy = sum(1 for v in health.values() if v["status"] == "healthy")
    logger.info(f"Ticker health: {healthy}/{len(TICKERS)} healthy")
    return health


def get_trend_data(bucket: str, days: int = 7) -> list:
    s3 = boto3.client("s3")
    today = datetime.now(timezone.utc).date()
    trends = []
    for i in range(days):
        day = today - timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        date_path = day.strftime("%Y/%m/%d")
        s3_key = f"monitoring/pipeline/{date_path}/summary.json"
        try:
            response = s3.get_object(Bucket=bucket, Key=s3_key)
            data = json.loads(response["Body"].read())
            data["date"] = date_str
            trends.append(data)
        except Exception:
            trends.append({"date": date_str, "success_rate_pct": 0.0, "quality_score_pct": 0.0})
    logger.info(f"Trend data loaded for {len(trends)} days")
    return trends


def generate_dashboard_html(kpis: dict, ticker_health: dict, trends: list) -> str:
    status_color = {"healthy": "#28a745", "warning": "#ffc107", "critical": "#dc3545"}
    ticker_rows = ""
    for ticker, health in ticker_health.items():
        color = status_color.get(health["status"], "#6c757d")
        ticker_rows += (
            f"<tr>"
            f"<td>{ticker}</td>"
            f"<td style='color:{color};font-weight:bold'>{health['status'].upper()}</td>"
            f"<td>{health['quality_score']:.1f}%</td>"
            f"<td>{health['last_updated']}</td>"
            f"</tr>"
        )
    trend_rows = ""
    for day in trends:
        trend_rows += (
            f"<tr>"
            f"<td>{day.get('date', '')}</td>"
            f"<td>{day.get('success_rate_pct', 0):.1f}%</td>"
            f"<td>{day.get('quality_score_pct', 0):.1f}%</td>"
            f"</tr>"
        )
    html = f"""<!DOCTYPE html>
<html>
<head><title>Stock Pipeline Dashboard</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }}
  .kpi-grid {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }}
  .kpi-card {{ background: white; border-radius: 8px; padding: 16px 24px; min-width: 160px;
               box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
  .kpi-value {{ font-size: 2em; font-weight: bold; color: #343a40; }}
  .kpi-label {{ color: #6c757d; font-size: 0.85em; }}
  table {{ border-collapse: collapse; width: 100%; background: white;
           border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
  th {{ background: #343a40; color: white; padding: 10px 14px; text-align: left; }}
  td {{ padding: 9px 14px; border-bottom: 1px solid #dee2e6; }}
  h2 {{ color: #343a40; margin-top: 28px; }}
</style>
</head>
<body>
<h1>Stock Pipeline Dashboard</h1>
<div class="kpi-grid">
  <div class="kpi-card"><div class="kpi-value">{kpis.get('success_rate_pct', 0):.1f}%</div>
    <div class="kpi-label">Success Rate</div></div>
  <div class="kpi-card"><div class="kpi-value">{kpis.get('quality_score_pct', 0):.1f}%</div>
    <div class="kpi-label">Quality Score</div></div>
  <div class="kpi-card"><div class="kpi-value">{kpis.get('sla_met_pct', 0):.1f}%</div>
    <div class="kpi-label">SLA Met</div></div>
  <div class="kpi-card"><div class="kpi-value">{kpis.get('anomaly_count', 0)}</div>
    <div class="kpi-label">Anomalies</div></div>
  <div class="kpi-card"><div class="kpi-value">{kpis.get('dlq_count', 0)}</div>
    <div class="kpi-label">DLQ Records</div></div>
  <div class="kpi-card"><div class="kpi-value">{kpis.get('total_runs', 0)}</div>
    <div class="kpi-label">Total Runs</div></div>
</div>
<h2>Ticker Health</h2>
<table>
  <tr><th>Ticker</th><th>Status</th><th>Quality Score</th><th>Last Updated</th></tr>
  {ticker_rows}
</table>
<h2>7-Day Trend</h2>
<table>
  <tr><th>Date</th><th>Success Rate</th><th>Quality Score</th></tr>
  {trend_rows}
</table>
</body>
</html>"""
    return html


def run_dashboard_update(bucket: str) -> str:
    s3 = boto3.client("s3")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    kpis = get_pipeline_kpis(bucket, today)
    ticker_health = get_ticker_health(bucket, today)
    trends = get_trend_data(bucket)
    html = generate_dashboard_html(kpis, ticker_health, trends)
    s3_key = "reports/dashboard/latest.html"
    s3.put_object(Bucket=bucket, Key=s3_key, Body=html, ContentType="text/html")
    s3_path = f"s3://{bucket}/{s3_key}"
    logger.info(f"Dashboard updated: {s3_path}")
    return s3_path


if __name__ == "__main__":
    pass
