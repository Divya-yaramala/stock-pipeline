import os
import json
import logging
from datetime import date, timedelta

import boto3
import pandas as pd
import yfinance as yf
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(path: str = "config/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def fetch_stock_data(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    logger.info(f"Fetching data for {tickers} from {start} to {end}")
    df = yf.download(tickers, start=start, end=end, group_by="ticker", auto_adjust=True)
    records = []
    for ticker in tickers:
        ticker_df = df[ticker].copy() if len(tickers) > 1 else df.copy()
        ticker_df["ticker"] = ticker
        ticker_df.reset_index(inplace=True)
        records.append(ticker_df)
    return pd.concat(records, ignore_index=True)


def upload_to_s3(df: pd.DataFrame, bucket: str, key: str) -> None:
    s3 = boto3.client("s3")
    csv_buffer = df.to_csv(index=False)
    s3.put_object(Bucket=bucket, Key=key, Body=csv_buffer)
    logger.info(f"Uploaded {len(df)} rows to s3://{bucket}/{key}")


def run(config_path: str = "config/config.yaml") -> None:
    cfg = load_config(config_path)
    tickers = cfg["stocks"]["tickers"]
    s3_bucket = cfg["aws"]["s3_bucket"]
    s3_prefix = cfg["aws"]["s3_prefix"]

    end = date.today().isoformat()
    start = (date.today() - timedelta(days=1)).isoformat()

    df = fetch_stock_data(tickers, start, end)
    s3_key = f"{s3_prefix}/{end}/stock_prices.csv"
    upload_to_s3(df, s3_bucket, s3_key)


if __name__ == "__main__":
    run()
