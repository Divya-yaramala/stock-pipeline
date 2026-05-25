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

AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def fetch_stock_data(ticker: str, period: str = "1d") -> pd.DataFrame:
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
    from ingestion import lineage_tracker, slack_alerter

    date = datetime.now().strftime("%Y/%m/%d")
    succeeded = 0
    failed = 0
    for ticker in TICKERS:
        start = time.time()
        try:
            df = fetch_stock_data(ticker)
            data = df.to_dict()
            if upload_to_s3(data, ticker, AWS_BUCKET_NAME, date):
                succeeded += 1
                slack_alerter.alert_pipeline_success("fetch", ticker, time.time() - start)
                lineage_tracker.record_lineage(
                    source="yahoo_finance_api",
                    destination="s3_raw",
                    ticker=ticker,
                    row_count=len(df),
                    transformation="extract_ohlcv",
                    bucket=AWS_BUCKET_NAME,
                )
            else:
                failed += 1
                slack_alerter.alert_pipeline_failure("fetch", ticker, "S3 upload failed")
        except Exception as e:
            logger.error(f"Pipeline error for {ticker}: {e}")
            failed += 1
            slack_alerter.alert_pipeline_failure("fetch", ticker, str(e))
            from ingestion import dead_letter_queue

            dead_letter_queue.send_to_dlq(str(e), ticker, "fetch", {}, AWS_BUCKET_NAME)
    logger.info(f"Pipeline complete: {succeeded} succeeded, {failed} failed")


if __name__ == "__main__":
    run_pipeline()
