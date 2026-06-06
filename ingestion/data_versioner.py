import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any

import boto3

from ingestion.config_manager import load_pipeline_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_version_id(ticker: str, date: str, data: dict) -> str:
    """
    Generate a reproducible 8-character MD5 version ID.

    Args:
        ticker: Stock ticker symbol.
        date: Date string in YYYY-MM-DD format.
        data: Dictionary of data to version.

    Returns:
        8-character hex string version ID.
    """
    raw = f"{ticker}{date}{json.dumps(data, sort_keys=True)}"
    version_id = hashlib.md5(raw.encode()).hexdigest()[:8]
    logger.info("Generated version ID %s for %s on %s", version_id, ticker, date)
    return version_id


def save_versioned_snapshot(
    data: dict,
    ticker: str,
    step: str,
    bucket: str,
    date: str,
) -> str:
    """
    Save a versioned snapshot of data to S3.

    Args:
        data: Data dictionary to snapshot.
        ticker: Stock ticker symbol.
        step: Pipeline step name (fetch, anomaly, prediction, insights).
        bucket: S3 bucket name.
        date: Date string in YYYY-MM-DD format.

    Returns:
        version_id string for the saved snapshot.
    """
    version_id = generate_version_id(ticker, date, data)
    date_parts = date.replace("-", "/")
    key = f"versions/{date_parts}/{step}/{ticker}_{version_id}.json"

    payload = {
        "data": data,
        "version_id": version_id,
        "ticker": ticker,
        "step": step,
        "created_at": datetime.utcnow().isoformat(),
    }

    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload),
        ContentType="application/json",
    )
    logger.info("Saved versioned snapshot %s to s3://%s/%s", version_id, bucket, key)
    return version_id


def list_versions(ticker: str, step: str, bucket: str, date: str) -> list:
    """
    List all saved versions for a ticker/step/date combination.

    Args:
        ticker: Stock ticker symbol.
        step: Pipeline step name.
        bucket: S3 bucket name.
        date: Date string in YYYY-MM-DD format.

    Returns:
        List of dicts with version_id and created_at fields.
    """
    date_parts = date.replace("-", "/")
    prefix = f"versions/{date_parts}/{step}/{ticker}_"

    s3 = boto3.client("s3")
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    objects = response.get("Contents", [])

    versions = []
    for obj in objects:
        key = obj["Key"]
        filename = key.split("/")[-1]
        version_id = filename.replace(f"{ticker}_", "").replace(".json", "")
        versions.append(
            {
                "version_id": version_id,
                "created_at": obj.get("LastModified", "").isoformat()
                if hasattr(obj.get("LastModified", ""), "isoformat")
                else str(obj.get("LastModified", "")),
            }
        )

    logger.info("Found %d versions for %s/%s on %s", len(versions), ticker, step, date)
    return versions


def rollback_to_version(
    ticker: str,
    step: str,
    version_id: str,
    bucket: str,
    date: str,
) -> dict:
    """
    Load a specific versioned snapshot from S3.

    Args:
        ticker: Stock ticker symbol.
        step: Pipeline step name.
        version_id: 8-character version ID to restore.
        bucket: S3 bucket name.
        date: Date string in YYYY-MM-DD format.

    Returns:
        Dictionary containing the versioned data payload.
    """
    date_parts = date.replace("-", "/")
    key = f"versions/{date_parts}/{step}/{ticker}_{version_id}.json"

    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    payload = json.loads(response["Body"].read().decode("utf-8"))

    logger.info("Rolled back %s/%s to version %s", ticker, step, version_id)
    return payload


def run_versioning_check() -> None:
    """List all versions for today across all configured tickers and log a summary."""
    pipeline_cfg = load_pipeline_config()
    bucket = os.getenv("AWS_S3_BUCKET", "")
    date = datetime.utcnow().strftime("%Y-%m-%d")
    steps = ["fetch", "anomaly", "prediction", "insights"]

    total_versions = 0
    tickers_with_versions = 0

    for ticker in pipeline_cfg.tickers:
        ticker_count = 0
        for step in steps:
            versions = list_versions(ticker, step, bucket, date)
            ticker_count += len(versions)
        if ticker_count > 0:
            tickers_with_versions += 1
        total_versions += ticker_count

    logger.info(
        "Versioning check complete: %d versions found across %d tickers",
        total_versions,
        tickers_with_versions,
    )


if __name__ == "__main__":
    run_versioning_check()
