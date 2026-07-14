import boto3
import json
import os
import logging
import datetime
from typing import Optional, Dict, List, Any, Callable
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EVENT_TYPES: List[str] = [
    "data_ingested",
    "anomaly_detected",
    "prediction_generated",
    "quality_gate_passed",
    "quality_gate_blocked",
    "sla_met",
    "sla_missed",
    "model_retrain_triggered",
    "pipeline_completed",
    "pipeline_failed",
]


def publish_event(
    event_type: str,
    payload: Dict[str, Any],
    source: str,
    bucket: str,
) -> str:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {event_type}. Must be one of {EVENT_TYPES}")
    s3 = boto3.client("s3")
    event_id = str(uuid.uuid4())
    published_at = datetime.datetime.utcnow().isoformat()
    event = {
        "event_id": event_id,
        "event_type": event_type,
        "payload": payload,
        "source": source,
        "published_at": published_at,
    }
    now = datetime.datetime.utcnow()
    date_path = now.strftime("%Y/%m/%d")
    key = f"events/{date_path}/{event_type}/{event_id}.json"
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(event))
    logger.info(f"Event published: {event_type} / {event_id}")
    return event_id


def get_events(event_type: str, bucket: str, date: str) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3")
    prefix = f"events/{date}/{event_type}/"
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    events = []
    for obj in response.get("Contents", []):
        key = str(obj["Key"])
        resp = s3.get_object(Bucket=bucket, Key=key)
        event = json.loads(resp["Body"].read())
        events.append(event)
    logger.info(f"Found {len(events)} events of type {event_type}")
    return events


def get_event_summary(bucket: str, date: str) -> Dict[str, Any]:
    by_type: Dict[str, int] = {}
    total = 0
    for event_type in EVENT_TYPES:
        events = get_events(event_type, bucket, date)
        count = len(events)
        by_type[event_type] = count
        total += count
    summary: Dict[str, Any] = {"total": total, "by_type": by_type, "date": date}
    logger.info(f"Event summary for {date}: {total} total events")
    return summary


def publish_pipeline_completed(ticker: str, duration_minutes: float, bucket: str) -> str:
    payload: Dict[str, Any] = {
        "ticker": ticker,
        "duration_minutes": float(duration_minutes),
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    return publish_event("pipeline_completed", payload, "pipeline", bucket)


def publish_anomaly_detected(
    ticker: str, anomaly_label: str, price: float, bucket: str
) -> str:
    payload: Dict[str, Any] = {
        "ticker": ticker,
        "anomaly_label": anomaly_label,
        "price": float(price),
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    return publish_event("anomaly_detected", payload, "ml_pipeline", bucket)


if __name__ == "__main__":
    pass
