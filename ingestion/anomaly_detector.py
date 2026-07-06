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

from ingestion.config_manager import load_aws_config, load_pipeline_config

AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

FEATURES = ["open", "high", "low", "close", "volume"]


def load_stock_data_from_s3(ticker: str, bucket: str, date: str) -> pd.DataFrame:
    """
    Load raw stock data for a ticker from S3 for the given date.

    Args:
        ticker: Stock ticker symbol.
        bucket: S3 bucket name.
        date: Date string in YYYY/MM/DD format.

    Returns:
        DataFrame of OHLCV data, or empty DataFrame on failure.
    """
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


def detect_anomalies(df: pd.DataFrame, ticker: str, contamination: float = 0.05) -> pd.DataFrame:
    """
    Run Isolation Forest anomaly detection on OHLCV features.

    Args:
        df: DataFrame with OHLCV columns.
        ticker: Stock ticker symbol (used for logging).
        contamination: Expected proportion of anomalies in the data.

    Returns:
        Copy of df with is_anomaly (bool) and anomaly_score (float) columns appended.
    """
    features = [col for col in FEATURES if col in df.columns]
    X = df[features].values
    model = IsolationForest(contamination=contamination, random_state=42)
    predictions = model.fit_predict(X)
    scores = model.decision_function(X)
    df = df.copy()
    df["is_anomaly"] = predictions == -1
    df["anomaly_score"] = scores
    anomaly_count = int(df["is_anomaly"].sum())
    logger.info(f"Detected {anomaly_count} anomalies for {ticker}")
    return df


def save_anomaly_results(df: pd.DataFrame, ticker: str, bucket: str, date: str) -> bool:
    """
    Upload anomaly-annotated DataFrame as JSON to S3.

    Args:
        df: DataFrame with anomaly columns added.
        ticker: Stock ticker symbol.
        bucket: S3 bucket name.
        date: Date string in YYYY/MM/DD format.

    Returns:
        True on success, False on failure.
    """
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
    """
    Detect anomalies for all configured tickers and save results to S3.

    Loads ticker list and configuration from config_manager, then for each ticker
    loads raw data, runs Isolation Forest, saves annotated results, and records
    lineage. Failed tickers are sent to the dead-letter queue and a Slack alert is
    fired.
    """
    from ingestion import lineage_tracker, slack_alerter

    try:
        aws_cfg = load_aws_config()
        bucket = aws_cfg.bucket_name
    except ValueError:
        bucket = AWS_BUCKET_NAME

    pipeline_cfg = load_pipeline_config()
    tickers = pipeline_cfg.tickers
    contamination = pipeline_cfg.anomaly_contamination

    date = datetime.now().strftime("%Y/%m/%d")
    total_anomalies = 0
    processed = 0
    for ticker in tickers:
        start = time.time()
        try:
            df = load_stock_data_from_s3(ticker, bucket, date)
            if df.empty:
                logger.warning(f"No data for {ticker}, skipping")
                continue
            df = detect_anomalies(df, ticker, contamination=contamination)
            total_anomalies += int(df["is_anomaly"].sum())
            anomaly_rows = df[df["is_anomaly"]]
            if not anomaly_rows.empty:
                try:
                    row = anomaly_rows.iloc[0]
                    slack_alerter.alert_anomaly_detected(
                        ticker=ticker,
                        anomaly_label="ISOLATION_FOREST",
                        price=float(str(row.get("close", 0.0))),
                        anomaly_score=float(str(row.get("anomaly_score", 0.0))),
                        date=date,
                    )
                except Exception:
                    pass
            if save_anomaly_results(df, ticker, bucket, date):
                processed += 1
                slack_alerter.alert_pipeline_success("anomaly", ticker, time.time() - start)
                lineage_tracker.record_lineage_event(
                    source_dataset="raw_prices",
                    target_dataset="anomaly_results",
                    transformation="isolation_forest",
                    ticker=ticker,
                    bucket=bucket,
                )
        except Exception as e:
            logger.error(f"Anomaly detection error for {ticker}: {e}")
            slack_alerter.alert_pipeline_failure("anomaly", str(e), ticker=ticker)
            from ingestion import dead_letter_queue

            dead_letter_queue.send_to_dlq(str(e), ticker, "anomaly", {}, bucket)
    logger.info(
        f"Anomaly detection complete: {processed} tickers processed, "
        f"{total_anomalies} anomalies found"
    )


if __name__ == "__main__":
    run_anomaly_detection()
