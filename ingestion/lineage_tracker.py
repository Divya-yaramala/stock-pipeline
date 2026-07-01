import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def record_lineage_event(
    source_dataset: str,
    target_dataset: str,
    transformation: str,
    ticker: str,
    bucket: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    now = datetime.now()
    recorded_at = now.isoformat()
    lineage_id = hashlib.md5(
        f"{source_dataset}{target_dataset}{transformation}{ticker}{recorded_at}".encode()
    ).hexdigest()
    date_path = now.strftime("%Y/%m/%d")
    key = f"lineage/{date_path}/{lineage_id}.json"
    record: Dict[str, Any] = {
        "lineage_id": lineage_id,
        "source_dataset": source_dataset,
        "target_dataset": target_dataset,
        "transformation": transformation,
        "ticker": ticker,
        "metadata": metadata or {},
        "recorded_at": recorded_at,
    }
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(record))
    logger.info(
        "Lineage event recorded: %s -> %s (%s)", source_dataset, target_dataset, lineage_id
    )
    return lineage_id


def _list_all_lineage_records(bucket: str, s3_client: Any) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix="lineage/")
    for obj in response.get("Contents", []):
        key = str(obj["Key"])
        if "/reports/" in key:
            continue
        try:
            body = s3_client.get_object(Bucket=bucket, Key=key)
            record = json.loads(body["Body"].read().decode("utf-8"))
            records.append(record)
        except Exception as e:
            logger.error("Failed to read lineage record %s: %s", key, e)
    return records


def get_dataset_lineage(
    dataset_name: str,
    bucket: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    upstream: List[Dict[str, Any]] = []
    downstream: List[Dict[str, Any]] = []

    for record in _list_all_lineage_records(bucket, s3):
        if str(record.get("target_dataset", "")) == dataset_name:
            upstream.append(record)
        if str(record.get("source_dataset", "")) == dataset_name:
            downstream.append(record)

    logger.info(
        "Lineage found for %s: %d upstream, %d downstream",
        dataset_name,
        len(upstream),
        len(downstream),
    )
    return {"upstream": upstream, "downstream": downstream}


def trace_data_flow(
    ticker: str,
    bucket: str,
    date: str,
) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    prefix = f"lineage/{date}/"
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    flows: List[Dict[str, Any]] = []
    for obj in response.get("Contents", []):
        key = str(obj["Key"])
        try:
            body = s3.get_object(Bucket=bucket, Key=key)
            record = json.loads(body["Body"].read().decode("utf-8"))
            if str(record.get("ticker", "")) == ticker:
                flows.append(record)
        except Exception as e:
            logger.error("Failed to read lineage record %s: %s", key, e)

    flows.sort(key=lambda r: str(r.get("recorded_at", "")))
    logger.info("Flow traced for %s on %s: %d events", ticker, date, len(flows))
    return flows


def find_impacted_datasets(
    source_dataset: str,
    bucket: str,
) -> List[str]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    all_records = _list_all_lineage_records(bucket, s3)

    impacted: Set[str] = set()
    to_check = [source_dataset]
    while to_check:
        current = to_check.pop()
        for record in all_records:
            if str(record.get("source_dataset", "")) == current:
                target = str(record.get("target_dataset", ""))
                if target not in impacted:
                    impacted.add(target)
                    to_check.append(target)

    result = list(impacted)
    logger.info(
        "Impact analysis complete: %s affects %d datasets", source_dataset, len(result)
    )
    return result


def generate_lineage_report(
    bucket: str,
    date: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    prefix = f"lineage/{date}/"
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)

    all_events: List[Dict[str, Any]] = []
    unique_datasets: Set[str] = set()

    for obj in response.get("Contents", []):
        key = str(obj["Key"])
        if "/reports/" in key:
            continue
        try:
            body = s3.get_object(Bucket=bucket, Key=key)
            record = json.loads(body["Body"].read().decode("utf-8"))
            all_events.append(record)
            unique_datasets.add(str(record.get("source_dataset", "")))
            unique_datasets.add(str(record.get("target_dataset", "")))
        except Exception as e:
            logger.error("Failed to read lineage record %s: %s", key, e)

    report: Dict[str, Any] = {
        "total_events": len(all_events),
        "unique_datasets": len(unique_datasets),
        "flows": all_events,
    }

    report_key = f"lineage/reports/{date}/report.json"
    s3.put_object(Bucket=bucket, Key=report_key, Body=json.dumps(report))
    logger.info(
        "Lineage report generated: %d events, %d datasets", len(all_events), len(unique_datasets)
    )
    return report


def run_lineage_tracking(
    ticker: str,
    bucket: str,
) -> None:
    pipeline_steps = [
        ("yahoo_finance", "raw_prices", "ingestion"),
        ("raw_prices", "validated_prices", "validation"),
        ("validated_prices", "postgres_staging", "loading"),
        ("postgres_staging", "snowflake_raw", "sync"),
        ("snowflake_raw", "snowflake_marts", "dbt"),
        ("validated_prices", "anomaly_results", "ml"),
        ("validated_prices", "predictions", "ml"),
        ("validated_prices", "sentiment_scores", "nlp"),
    ]
    for source, target, transformation in pipeline_steps:
        record_lineage_event(source, target, transformation, ticker, bucket)
    logger.info("All lineage events recorded for ticker %s", ticker)


if __name__ == "__main__":
    pass
