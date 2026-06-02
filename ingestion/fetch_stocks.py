import json
import logging
import os
import time
from datetime import datetime

import boto3
import pandas as pd
import yfinance as yf

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from ingestion.config_manager import load_aws_config, load_pipeline_config

AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def fetch_stock_data(ticker: str, period: str = "1d") -> pd.DataFrame:
    """
    Download OHLCV data for a ticker from Yahoo Finance.

    Args:
        ticker: Stock ticker symbol.
        period: yfinance period string (e.g. '1d', '5d').

    Returns:
        DataFrame of OHLCV data for the requested period.

    Raises:
        ValueError: If yfinance returns an empty DataFrame.
        Exception: On unexpected yfinance errors.
    """
    try:
        df = yf.download(ticker, period=period, progress=False)
        if df.empty:
            raise ValueError(f"No data returned for ticker: {ticker}")
        logger.info(f"Successfully fetched data for {ticker}")
        return df
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch data for {ticker}: {e}")
        raise


def upload_to_s3(data: dict, ticker: str, bucket: str, date: str) -> bool:
    """
    Serialize data dict as JSON and upload to S3.

    Args:
        data: Dict of OHLCV data to upload.
        ticker: Stock ticker symbol.
        bucket: S3 bucket name.
        date: Date string in YYYY/MM/DD format.

    Returns:
        True on success, False on failure.
    """
    try:
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        key = f"raw/stocks/{date}/{ticker}.json"
        json_str = json.dumps(data)
        s3_client.put_object(Bucket=bucket, Key=key, Body=json_str)
        logger.info(f"Uploaded to s3://{bucket}/{key}")
        return True
    except Exception as e:
        logger.error(f"Failed to upload {ticker} to S3: {e}")
        return False


def run_pipeline() -> None:
    """
    Fetch daily stock data for all configured tickers and upload each to S3.

    Loads configuration from config_manager. Succeeded and failed counts are
    logged at the end. Failed tickers are sent to the dead-letter queue and a
    Slack failure alert is fired.
    """
    from ingestion import lineage_tracker, slack_alerter

    try:
        aws_cfg = load_aws_config()
        bucket = aws_cfg.bucket_name
        region = aws_cfg.region
    except ValueError:
        bucket = AWS_BUCKET_NAME
        region = AWS_REGION

    pipeline_cfg = load_pipeline_config()
    tickers = pipeline_cfg.tickers
    raw_prefix = pipeline_cfg.s3_raw_prefix

    date = datetime.now().strftime("%Y/%m/%d")
    succeeded = 0
    failed = 0
    for ticker in tickers:
        start = time.time()
        try:
            df = fetch_stock_data(ticker)
            data = df.to_dict()
            key_prefix = f"{raw_prefix}/{date}"
            s3_client = boto3.client("s3", region_name=region)
            key = f"{key_prefix}/{ticker}.json"
            s3_client.put_object(Bucket=bucket, Key=key, Body=json.dumps(data))
            succeeded += 1
            slack_alerter.alert_pipeline_success("fetch", ticker, time.time() - start)
            lineage_tracker.record_lineage(
                source="yahoo_finance_api",
                destination="s3_raw",
                ticker=ticker,
                row_count=len(df),
                transformation="extract_ohlcv",
                bucket=bucket,
            )
        except Exception as e:
            logger.error(f"Pipeline error for {ticker}: {e}")
            failed += 1
            slack_alerter.alert_pipeline_failure("fetch", ticker, str(e))
            from ingestion import dead_letter_queue

            dead_letter_queue.send_to_dlq(str(e), ticker, "fetch", {}, bucket)
    logger.info(f"Pipeline complete: {succeeded} succeeded, {failed} failed")


if __name__ == "__main__":
    run_pipeline()
