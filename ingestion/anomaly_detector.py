import json
import logging
import os
import time
from datetime import datetime

import boto3
import pandas as pd
from sklearn.ensemble import IsolationForest

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
FEATURES = ["open", "high", "low", "close", "volume"]


def load_stock_data_from_s3(ticker: str, bucket: str, date: str) -> pd.DataFrame:
    try:
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        key = f"raw/stocks/{date}/{ticker}.json"
        response = s3_client.get_object(Bucket=bucket, Key=key)
        data = json.loads(response["Body"].read().decode("utf-8"))
        df = pd.DataFrame(data)
        df.columns = [col.lower() for col in df.columns]
        logger.info(f"Loaded {len(df)} rows for {ticker} from s3://{bucket}/{key}")
        return df
    except Exception as e:
        logger.error(f"Failed to load {ticker} from S3: {e}")
        return pd.DataFrame()


def detect_anomalies(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    features = [col for col in FEATURES if col in df.columns]
    X = df[features].values
    model = IsolationForest(contamination=0.05, random_state=42)
    predictions = model.fit_predict(X)
    scores = model.decision_function(X)
    df = df.copy()
    df["is_anomaly"] = predictions == -1
    df["anomaly_score"] = scores
    anomaly_count = int(df["is_anomaly"].sum())
    logger.info(f"Detected {anomaly_count} anomalies for {ticker}")
    return df


def save_anomaly_results(df: pd.DataFrame, ticker: str, bucket: str, date: str) -> bool:
    try:
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        key = f"processed/anomalies/{date}/{ticker}.json"
        json_str = df.to_json()
        s3_client.put_object(Bucket=bucket, Key=key, Body=json_str)
        logger.info(f"Saved anomaly results to s3://{bucket}/{key}")
        return True
    except Exception as e:
        logger.error(f"Failed to save anomaly results for {ticker}: {e}")
        return False


def run_anomaly_detection() -> None:
    from ingestion import lineage_tracker, slack_alerter

    date = datetime.now().strftime("%Y/%m/%d")
    total_anomalies = 0
    processed = 0
    for ticker in TICKERS:
        start = time.time()
        try:
            df = load_stock_data_from_s3(ticker, AWS_BUCKET_NAME, date)
            if df.empty:
                logger.warning(f"No data for {ticker}, skipping")
                continue
            df = detect_anomalies(df, ticker)
            total_anomalies += int(df["is_anomaly"].sum())
            if save_anomaly_results(df, ticker, AWS_BUCKET_NAME, date):
                processed += 1
                slack_alerter.alert_pipeline_success("anomaly", ticker, time.time() - start)
                lineage_tracker.record_lineage(
                    source="s3_raw",
                    destination="s3_processed_anomalies",
                    ticker=ticker,
                    row_count=len(df),
                    transformation="isolation_forest",
                    bucket=AWS_BUCKET_NAME,
                )
        except Exception as e:
            logger.error(f"Anomaly detection error for {ticker}: {e}")
            slack_alerter.alert_pipeline_failure("anomaly", ticker, str(e))
            from ingestion import dead_letter_queue

            dead_letter_queue.send_to_dlq(str(e), ticker, "anomaly", {}, AWS_BUCKET_NAME)
    logger.info(
        f"Anomaly detection complete: {processed} tickers processed, "
        f"{total_anomalies} anomalies found"
    )


if __name__ == "__main__":
    run_anomaly_detection()
