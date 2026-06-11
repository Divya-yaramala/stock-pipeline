import json
import logging
import os
from datetime import datetime, timedelta

import boto3
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def load_raw_features(ticker: str, bucket: str, days: int = 60) -> pd.DataFrame:
    s3 = boto3.client("s3")
    today = datetime.utcnow().date()
    rows = []

    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y/%m/%d")
        key = f"raw/stocks/{date_str}/{ticker}.json"
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            records = json.loads(response["Body"].read().decode("utf-8"))
            if isinstance(records, list) and records:
                record = records[0]
            elif isinstance(records, dict):
                record = records
            else:
                continue
            rows.append(
                {
                    "date": str(date),
                    "open": float(record.get("open", 0)),
                    "high": float(record.get("high", 0)),
                    "low": float(record.get("low", 0)),
                    "close": float(record.get("close", 0)),
                    "volume": float(record.get("volume", 0)),
                }
            )
        except Exception:
            pass

    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df.sort_values("date", inplace=True)
        df.reset_index(drop=True, inplace=True)

    logger.info("Loaded %d rows of raw features for %s", len(df), ticker)
    return df


def add_price_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["daily_return"] = (df["close"] - df["open"]) / df["open"] * 100
    df["high_low_range"] = df["high"] - df["low"]
    range_denom = df["high"] - df["low"]
    df["price_position"] = (df["close"] - df["low"]) / range_denom.where(
        range_denom != 0, other=np.nan
    )
    df["gap_up"] = df["open"] > df["close"].shift(1)
    df["body_size"] = (df["close"] - df["open"]).abs()
    return df


def add_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["volume_sma_20"] = df["volume"].rolling(window=20).mean()
    df["volume_ratio"] = df["volume"] / df["volume_sma_20"]
    df["high_volume"] = df["volume_ratio"] > 1.5
    return df


def add_momentum_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["roc_5"] = df["close"].pct_change(periods=5) * 100
    df["roc_10"] = df["close"].pct_change(periods=10) * 100
    df["momentum_signal"] = df["roc_5"].apply(lambda x: "UP" if x > 0 else "DOWN")
    return df


def create_feature_matrix(ticker: str, bucket: str) -> pd.DataFrame:
    df = load_raw_features(ticker, bucket)
    if df.empty:
        logger.warning("No raw data found for %s — returning empty DataFrame", ticker)
        return df

    df = add_price_features(df)
    df = add_volume_features(df)
    df = add_momentum_features(df)
    df = df.dropna().reset_index(drop=True)

    logger.info(
        "Feature matrix for %s: %d features, %d rows",
        ticker,
        len(df.columns),
        len(df),
    )

    if bucket:
        try:
            s3 = boto3.client("s3")
            date_str = datetime.utcnow().strftime("%Y/%m/%d")
            key = f"processed/features/{date_str}/{ticker}.json"
            records = df.astype(str).to_dict(orient="records")
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(records, indent=2).encode("utf-8"),
                ContentType="application/json",
            )
            logger.info("Saved feature matrix for %s to s3://%s/%s", ticker, bucket, key)
        except Exception as e:
            logger.error("Failed to save feature matrix for %s: %s", ticker, e)

    return df


if __name__ == "__main__":
    _bucket = os.getenv("AWS_BUCKET_NAME", "")
    pass
