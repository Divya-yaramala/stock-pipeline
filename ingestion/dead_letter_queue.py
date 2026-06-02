"""
Dead Letter Queue (DLQ) Pattern
--------------------------------
When a pipeline step fails for a specific ticker, instead of
stopping the entire pipeline, the failed record is saved to S3
under errors/YYYY/MM/DD/step/. This allows:
- Other tickers to continue processing
- Failed records to be replayed later without rerunning the full pipeline
- Full audit trail of all failures
"""

import json
import logging
import os
from datetime import datetime

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def send_to_dlq(error: str, ticker: str, step: str, payload: dict, bucket: str) -> bool:
    """
    Save a failed record to S3 under errors/YYYY/MM/DD/step/ticker_timestamp.json.

    Args:
        error: Error message string describing the failure.
        ticker: Stock ticker symbol that failed.
        step: Pipeline step name (e.g. 'fetch', 'anomaly').
        payload: Original data payload that caused the failure.
        bucket: S3 bucket name for the DLQ.

    Returns:
        True if the record was saved successfully, False otherwise.
    """
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date = datetime.now().strftime("%Y/%m/%d")
        key = f"errors/{date}/{step}/{ticker}_{timestamp}.json"
        record = {
            "ticker": ticker,
            "step": step,
            "error": error,
            "payload": payload,
            "failed_at": datetime.now().isoformat(),
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(record))
        logger.info("DLQ record saved to s3://%s/%s", bucket, key)
        return True
    except Exception as e:
        logger.error("Failed to send to DLQ for %s/%s: %s", ticker, step, e)
        return False


def get_dlq_records(bucket: str, date: str) -> list:
    """
    List and download all failed records from S3 for the given date.

    Args:
        bucket: S3 bucket name containing DLQ records.
        date: Date string in YYYY/MM/DD format.

    Returns:
        List of DLQ record dicts; empty list if none found or on S3 error.
    """
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        prefix = f"errors/{date}/"
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        contents = response.get("Contents", [])
        records = []
        for obj in contents:
            try:
                body = s3.get_object(Bucket=bucket, Key=obj["Key"])
                record = json.loads(body["Body"].read().decode("utf-8"))
                records.append(record)
            except Exception as e:
                logger.error("Failed to read DLQ record %s: %s", obj["Key"], e)
        logger.info("Found %d failed records in DLQ", len(records))
        return records
    except Exception as e:
        logger.error("Failed to list DLQ records: %s", e)
        return []


def replay_dlq_record(record: dict) -> bool:
    """
    Replay a single DLQ record by re-running the appropriate pipeline step.

    Args:
        record: DLQ record dict containing at minimum 'step' and 'ticker' keys.

    Returns:
        True if the replay succeeded, False if the step is unknown or replay raised.
    """
    step = record.get("step", "")
    ticker = record.get("ticker", "")
    logger.info("Replaying DLQ record for %s/%s", ticker, step)
    try:
        if step == "fetch":
            from ingestion import fetch_stocks

            fetch_stocks.run_pipeline()
        elif step == "anomaly":
            from ingestion import anomaly_detector

            anomaly_detector.run_anomaly_detection()
        elif step == "prediction":
            from ingestion import price_predictor

            price_predictor.run_price_prediction()
        elif step == "insights":
            from ingestion import market_insights

            market_insights.run_market_insights()
        else:
            logger.warning("Unknown step '%s' for DLQ record", step)
            return False
        logger.info("Replay successful for %s/%s", ticker, step)
        return True
    except Exception as e:
        logger.error("Replay failed for %s/%s: %s", ticker, step, e)
        return False


def run_dlq_replay() -> None:
    """
    Replay all DLQ records for today and log the final summary.

    Reads today's failed records from S3, attempts to replay each one, and logs
    the count of successful replays versus records that are still failing.
    """
    bucket = os.environ.get("AWS_BUCKET_NAME", "")
    date = datetime.now().strftime("%Y/%m/%d")
    records = get_dlq_records(bucket, date)
    if not records:
        logger.info("No DLQ records to replay")
        return
    replayed = 0
    still_failing = 0
    for record in records:
        if replay_dlq_record(record):
            replayed += 1
        else:
            still_failing += 1
    logger.info("%d replayed successfully, %d still failing", replayed, still_failing)


if __name__ == "__main__":
    run_dlq_replay()
