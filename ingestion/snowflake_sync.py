import json
import logging
import os
from datetime import datetime

import boto3
import pandas as pd
import snowflake.connector

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def _get_snowflake_connection():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "STOCK_PIPELINE_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "STOCK_PIPELINE_DB"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "MARTS"),
        role=os.environ.get("SNOWFLAKE_ROLE", "SYSADMIN"),
    )


def load_from_s3(bucket: str, key: str) -> dict:
    """Downloads JSON from S3 and returns it as a dict."""
    s3 = boto3.client("s3", region_name=AWS_REGION)
    response = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(response["Body"].read().decode("utf-8"))


def sync_stock_prices(conn, ticker: str, date: str) -> bool:
    """Loads raw stock data from S3 and inserts into Snowflake RAW.STOCK_PRICES."""
    try:
        bucket = os.environ.get("AWS_BUCKET_NAME", "")
        key = f"raw/stocks/{date}/{ticker}.json"
        data = load_from_s3(bucket, key)

        trade_date = date.replace("/", "-")
        opens = data.get("Open") or data.get("open") or {}
        highs = data.get("High") or data.get("high") or {}
        lows = data.get("Low") or data.get("low") or {}
        closes = data.get("Close") or data.get("close") or {}
        volumes = data.get("Volume") or data.get("volume") or {}

        open_val = next(iter(opens.values()), None)
        high_val = next(iter(highs.values()), None)
        low_val = next(iter(lows.values()), None)
        close_val = next(iter(closes.values()), None)
        volume_val = next(iter(volumes.values()), None)

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO STOCK_PIPELINE_DB.RAW.STOCK_PRICES
                (TICKER, TRADE_DATE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, CLOSE_PRICE, VOLUME)
            SELECT %s, %s::DATE, %s, %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM STOCK_PIPELINE_DB.RAW.STOCK_PRICES
                WHERE TICKER = %s AND TRADE_DATE = %s::DATE
            )
            """,
            (
                ticker,
                trade_date,
                open_val,
                high_val,
                low_val,
                close_val,
                volume_val,
                ticker,
                trade_date,
            ),
        )
        cur.close()
        logger.info("Synced stock prices for %s on %s", ticker, trade_date)
        return True
    except Exception as e:
        logger.error("Failed to sync stock prices for %s: %s", ticker, e)
        return False


def sync_anomalies(conn, ticker: str, date: str) -> bool:
    """Loads anomaly results from S3 and inserts into Snowflake RAW.STOCK_ANOMALIES."""
    try:
        bucket = os.environ.get("AWS_BUCKET_NAME", "")
        key = f"processed/anomalies/{date}/{ticker}.json"
        data = load_from_s3(bucket, key)

        trade_date = date.replace("/", "-")
        is_anomaly_col = data.get("is_anomaly") or {}
        anomaly_score_col = data.get("anomaly_score") or {}

        is_anomaly = bool(next(iter(is_anomaly_col.values()), False))
        anomaly_score = next(iter(anomaly_score_col.values()), None)

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO STOCK_PIPELINE_DB.RAW.STOCK_ANOMALIES
                (TICKER, TRADE_DATE, IS_ANOMALY, ANOMALY_SCORE)
            SELECT %s, %s::DATE, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM STOCK_PIPELINE_DB.RAW.STOCK_ANOMALIES
                WHERE TICKER = %s AND TRADE_DATE = %s::DATE
            )
            """,
            (ticker, trade_date, is_anomaly, anomaly_score, ticker, trade_date),
        )
        cur.close()
        logger.info("Synced anomalies for %s on %s", ticker, trade_date)
        return True
    except Exception as e:
        logger.error("Failed to sync anomalies for %s: %s", ticker, e)
        return False


def sync_predictions(conn, ticker: str, date: str) -> bool:
    """Loads predictions from S3 and inserts into Snowflake RAW.STOCK_PREDICTIONS."""
    try:
        bucket = os.environ.get("AWS_BUCKET_NAME", "")
        key = f"processed/predictions/{date}/{ticker}.json"
        data = load_from_s3(bucket, key)

        trade_date = date.replace("/", "-")
        yhat_col = data.get("yhat") or {}
        ds_col = data.get("ds") or {}
        yhat_lower_col = data.get("yhat_lower") or {}
        yhat_upper_col = data.get("yhat_upper") or {}

        cur = conn.cursor()
        for idx in yhat_col:
            prediction_date = ds_col.get(idx, trade_date)
            if isinstance(prediction_date, (int, float)):
                prediction_date = pd.to_datetime(prediction_date, unit="ms").strftime("%Y-%m-%d")
            elif "T" in str(prediction_date):
                prediction_date = str(prediction_date)[:10]

            cur.execute(
                """
                INSERT INTO STOCK_PIPELINE_DB.RAW.STOCK_PREDICTIONS
                    (TICKER, PREDICTION_DATE, PREDICTED_CLOSE, LOWER_BOUND, UPPER_BOUND)
                SELECT %s, %s::DATE, %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM STOCK_PIPELINE_DB.RAW.STOCK_PREDICTIONS
                    WHERE TICKER = %s AND PREDICTION_DATE = %s::DATE
                )
                """,
                (
                    ticker,
                    prediction_date,
                    yhat_col.get(idx),
                    yhat_lower_col.get(idx),
                    yhat_upper_col.get(idx),
                    ticker,
                    prediction_date,
                ),
            )
        cur.close()
        logger.info("Synced predictions for %s on %s", ticker, trade_date)
        return True
    except Exception as e:
        logger.error("Failed to sync predictions for %s: %s", ticker, e)
        return False


def sync_insights(conn, ticker: str, date: str) -> bool:
    """Loads insights from S3 and inserts into Snowflake RAW.STOCK_INSIGHTS."""
    try:
        bucket = os.environ.get("AWS_BUCKET_NAME", "")
        key = f"processed/insights/{date}/{ticker}.json"
        data = load_from_s3(bucket, key)

        insight_date = date.replace("/", "-")
        insight_text = data.get("insight", "")

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO STOCK_PIPELINE_DB.RAW.STOCK_INSIGHTS
                (TICKER, INSIGHT_DATE, INSIGHT_TEXT)
            SELECT %s, %s::DATE, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM STOCK_PIPELINE_DB.RAW.STOCK_INSIGHTS
                WHERE TICKER = %s AND INSIGHT_DATE = %s::DATE
            )
            """,
            (ticker, insight_date, insight_text, ticker, insight_date),
        )
        cur.close()
        logger.info("Synced insights for %s on %s", ticker, insight_date)
        return True
    except Exception as e:
        logger.error("Failed to sync insights for %s: %s", ticker, e)
        return False


def run_snowflake_sync() -> None:
    date = datetime.now().strftime("%Y/%m/%d")
    conn = _get_snowflake_connection()
    synced = 0
    for ticker in TICKERS:
        if sync_stock_prices(conn, ticker, date):
            synced += 1
        if sync_anomalies(conn, ticker, date):
            synced += 1
        if sync_predictions(conn, ticker, date):
            synced += 1
        if sync_insights(conn, ticker, date):
            synced += 1
    conn.close()
    logger.info("%d records synced to Snowflake", synced)


if __name__ == "__main__":
    run_snowflake_sync()
