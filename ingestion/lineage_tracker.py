import json
import logging
import os
from datetime import datetime

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from ingestion.config_manager import load_pipeline_config

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def record_lineage(
    source: str,
    destination: str,
    ticker: str,
    row_count: int,
    transformation: str,
    bucket: str,
) -> bool:
    """
    Save a lineage record to S3 at lineage/YYYY/MM/DD/ticker_timestamp.json.

    Args:
        source: Name of the data source (e.g. 'yahoo_finance_api', 's3_raw').
        destination: Name of the data destination (e.g. 's3_processed_anomalies').
        ticker: Stock ticker symbol.
        row_count: Number of rows processed in this step.
        transformation: Name of the transformation applied (e.g. 'isolation_forest').
        bucket: S3 bucket name.

    Returns:
        True if the record was saved successfully, False otherwise.
    """
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date = datetime.now().strftime("%Y/%m/%d")
        key = f"lineage/{date}/{ticker}_{timestamp}.json"
        record = {
            "source": source,
            "destination": destination,
            "ticker": ticker,
            "row_count": row_count,
            "transformation": transformation,
            "recorded_at": datetime.now().isoformat(),
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(record))
        logger.info("Lineage record saved to s3://%s/%s", bucket, key)
        return True
    except Exception as e:
        logger.error("Failed to record lineage for %s: %s", ticker, e)
        return False


def get_lineage_for_ticker(ticker: str, bucket: str, date: str) -> list:
    """
    Fetch all lineage records for a ticker on a given date, ordered by recorded_at.

    Args:
        ticker: Stock ticker symbol.
        bucket: S3 bucket name.
        date: Date string in YYYY/MM/DD format.

    Returns:
        List of lineage record dicts sorted ascending by recorded_at; empty on error.
    """
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        prefix = f"lineage/{date}/{ticker}_"
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        contents = response.get("Contents", [])
        records = []
        for obj in contents:
            try:
                body = s3.get_object(Bucket=bucket, Key=obj["Key"])
                record = json.loads(body["Body"].read().decode("utf-8"))
                records.append(record)
            except Exception as e:
                logger.error("Failed to read lineage record %s: %s", obj["Key"], e)
        records.sort(key=lambda r: r.get("recorded_at", ""))
        logger.info("Lineage chain for %s (%d records): %s", ticker, len(records), records)
        return records
    except Exception as e:
        logger.error("Failed to list lineage records for %s: %s", ticker, e)
        return []


def generate_lineage_report(bucket: str, date: str) -> dict:
    """
    Build a full lineage report for all configured tickers on the given date.

    Args:
        bucket: S3 bucket name.
        date: Date string in YYYY/MM/DD format.

    Returns:
        Dict mapping each ticker to its list of lineage records for the day.
    """
    pipeline_cfg = load_pipeline_config()
    report = {}
    total = 0
    for ticker in pipeline_cfg.tickers:
        records = get_lineage_for_ticker(ticker, bucket, date)
        report[ticker] = records
        total += len(records)
    logger.info("%d lineage records captured today", total)
    return report


if __name__ == "__main__":
    generate_lineage_report(
        os.getenv("AWS_BUCKET_NAME", ""),
        datetime.now().strftime("%Y/%m/%d"),
    )
