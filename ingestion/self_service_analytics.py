import datetime
import json
import logging
import os
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AVAILABLE_METRICS: List[Dict[str, Any]] = [
    {
        "metric_id": "M001",
        "name": "price_return_pct",
        "description": "Daily price return %",
        "category": "price",
    },
    {
        "metric_id": "M002",
        "name": "volatility_20d",
        "description": "20-day rolling volatility",
        "category": "risk",
    },
    {
        "metric_id": "M003",
        "name": "anomaly_rate_pct",
        "description": "% days with anomaly",
        "category": "quality",
    },
    {
        "metric_id": "M004",
        "name": "sentiment_score",
        "description": "News sentiment score",
        "category": "nlp",
    },
    {
        "metric_id": "M005",
        "name": "prediction_accuracy_pct",
        "description": "Forecast accuracy %",
        "category": "ml",
    },
    {
        "metric_id": "M006",
        "name": "quality_score",
        "description": "Overall data quality score",
        "category": "quality",
    },
    {
        "metric_id": "M007",
        "name": "sla_compliance_pct",
        "description": "SLA compliance %",
        "category": "operations",
    },
    {
        "metric_id": "M008",
        "name": "pipeline_duration_minutes",
        "description": "Pipeline run duration",
        "category": "operations",
    },
]


def list_available_metrics() -> List[Dict[str, Any]]:
    logger.info(f"Available metrics: {len(AVAILABLE_METRICS)}")
    return AVAILABLE_METRICS


def query_metric(
    metric_id: str,
    ticker: str,
    start_date: str,
    end_date: str,
    bucket: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    prefix = f"metrics/{metric_id}/{ticker}/"
    values: List[Any] = []
    dates: List[str] = []
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        for obj in response.get("Contents", []):
            key = str(obj["Key"])
            date_part = key.split("/")[-1].replace(".json", "")
            if start_date <= date_part <= end_date:
                resp = s3.get_object(Bucket=bucket, Key=key)
                record = json.loads(resp["Body"].read())
                values.append(record.get("value"))
                dates.append(date_part)
    except Exception as e:
        logger.error(f"Failed to query metric {metric_id} for {ticker}: {e}")

    logger.info(f"Query executed: {metric_id} / {ticker} | {len(values)} data points")
    return {"metric_id": metric_id, "ticker": ticker, "values": values, "dates": dates}


def compare_metrics(
    metric_id: str,
    tickers: List[str],
    date: str,
    bucket: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    by_ticker: Dict[str, Any] = {}
    leader = ""
    best_value: Optional[float] = None

    for ticker in tickers:
        key = f"metrics/{metric_id}/{ticker}/{date}.json"
        try:
            resp = s3.get_object(Bucket=bucket, Key=key)
            record = json.loads(resp["Body"].read())
            value = float(str(record.get("value", 0.0)))
            by_ticker[ticker] = value
            if best_value is None or value > best_value:
                best_value = value
                leader = ticker
        except Exception:
            by_ticker[ticker] = None

    logger.info(f"Comparison complete: {metric_id} | leader={leader}")
    return {"metric_id": metric_id, "date": date, "by_ticker": by_ticker, "leader": leader}


def build_custom_report(
    metrics: List[str],
    tickers: List[str],
    date: str,
    bucket: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    report: Dict[str, Any] = {}

    for ticker in tickers:
        report[ticker] = {}
        for metric_id in metrics:
            key = f"metrics/{metric_id}/{ticker}/{date}.json"
            try:
                resp = s3.get_object(Bucket=bucket, Key=key)
                record = json.loads(resp["Body"].read())
                report[ticker][metric_id] = record.get("value")
            except Exception:
                report[ticker][metric_id] = None

    now = datetime.datetime.utcnow()
    timestamp = now.strftime("%Y%m%dT%H%M%S")
    date_path = now.strftime("%Y/%m/%d")
    save_key = f"reports/custom/{date_path}/report_{timestamp}.json"
    try:
        s3.put_object(Bucket=bucket, Key=save_key, Body=json.dumps(report))
    except Exception as e:
        logger.error(f"Failed to save custom report: {e}")

    logger.info(f"Custom report built: {len(tickers)} tickers × {len(metrics)} metrics")
    return report


def get_metric_trends(
    metric_id: str,
    ticker: str,
    days: int,
    bucket: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    values: List[float] = []
    dates: List[str] = []

    for i in range(days):
        day = datetime.datetime.utcnow() - datetime.timedelta(days=days - 1 - i)
        date_str = day.strftime("%Y-%m-%d")
        key = f"metrics/{metric_id}/{ticker}/{date_str}.json"
        try:
            resp = s3.get_object(Bucket=bucket, Key=key)
            record = json.loads(resp["Body"].read())
            values.append(float(str(record.get("value", 0.0))))
            dates.append(date_str)
        except Exception:
            pass

    avg = float(sum(values)) / len(values) if values else 0.0
    min_val = min(values) if values else 0.0
    max_val = max(values) if values else 0.0

    if len(values) >= 2:
        trend = "up" if values[-1] > values[0] else "down" if values[-1] < values[0] else "flat"
    else:
        trend = "insufficient_data"

    logger.info(f"Trend analysis complete: {metric_id} / {ticker} | trend={trend}")
    return {
        "metric_id": metric_id,
        "ticker": ticker,
        "days": days,
        "values": values,
        "dates": dates,
        "trend": trend,
        "avg": avg,
        "min": min_val,
        "max": max_val,
    }


def run_self_service_demo(bucket: str) -> Dict[str, Any]:
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    metrics = [str(m["metric_id"]) for m in AVAILABLE_METRICS]
    date = datetime.datetime.utcnow().strftime("%Y/%m/%d")

    list_available_metrics()
    report = build_custom_report(metrics, tickers, date, bucket)

    logger.info("Self-Service Demo Complete")
    return report


if __name__ == "__main__":
    pass
