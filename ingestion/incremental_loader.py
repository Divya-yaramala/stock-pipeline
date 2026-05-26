import json
import logging
import os
from datetime import datetime, timedelta

import boto3
import yfinance as yf

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

INSERT_SQL = """
    INSERT INTO staging.stock_prices_raw
        (ticker, trade_date, open_price, high_price, low_price, close_price, volume)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (ticker, trade_date) DO NOTHING
"""


def get_last_loaded_date(ticker: str, conn) -> str | None:
    """Return MAX(trade_date) for ticker from Postgres, or None if no rows exist."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(trade_date) FROM staging.stock_prices_raw WHERE ticker = %s",
            (ticker,),
        )
        result = cur.fetchone()
    if result and result[0]:
        date_str = result[0].strftime("%Y-%m-%d")
        logger.info("Last loaded date for %s: %s", ticker, date_str)
        return date_str
    logger.info("No data found in Postgres for %s", ticker)
    return None


def get_missing_dates(ticker: str, conn) -> list:
    """Return weekday dates (YYYY/MM/DD) between last loaded date and yesterday."""
    last_date_str = get_last_loaded_date(ticker, conn)
    if not last_date_str:
        logger.info("No baseline date for %s — skipping gap detection", ticker)
        return []

    last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
    yesterday = (datetime.now() - timedelta(days=1)).date()

    missing = []
    current = last_date + timedelta(days=1)
    while current <= yesterday:
        if current.weekday() < 5:
            missing.append(current.strftime("%Y/%m/%d"))
        current += timedelta(days=1)

    logger.info("Found %d missing dates for %s", len(missing), ticker)
    return missing


def backfill_ticker(ticker: str, conn, bucket: str, start_date: str, end_date: str) -> int:
    """Download historical data from yfinance, upload to S3, and insert into Postgres.

    start_date / end_date must be in YYYY-MM-DD format. end_date is exclusive (yfinance).
    Returns number of rows successfully loaded.
    """
    s3 = boto3.client("s3", region_name=AWS_REGION)
    df = yf.download(ticker, start=start_date, end=end_date, progress=False)

    if df.empty:
        logger.warning(
            "No data from yfinance for %s between %s and %s", ticker, start_date, end_date
        )
        return 0

    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)
    df.columns = [col.lower() for col in df.columns]

    rows_loaded = 0
    for i, (date_idx, row) in enumerate(df.iterrows()):
        try:
            date_slash = date_idx.strftime("%Y/%m/%d")
            trade_date = date_idx.strftime("%Y-%m-%d")
            key = f"raw/stocks/{date_slash}/{ticker}.json"

            day_data = {
                "open": {trade_date: float(row.get("open") or 0)},
                "high": {trade_date: float(row.get("high") or 0)},
                "low": {trade_date: float(row.get("low") or 0)},
                "close": {trade_date: float(row.get("close") or 0)},
                "volume": {trade_date: int(row.get("volume") or 0)},
            }
            s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(day_data))

            with conn.cursor() as cur:
                cur.execute(
                    INSERT_SQL,
                    (
                        ticker,
                        trade_date,
                        float(row.get("open") or 0),
                        float(row.get("high") or 0),
                        float(row.get("low") or 0),
                        float(row.get("close") or 0),
                        int(row.get("volume") or 0),
                    ),
                )
            conn.commit()
            rows_loaded += 1

            if (i + 1) % 10 == 0:
                logger.info("Backfilled %d/%d rows for %s", i + 1, len(df), ticker)
        except Exception as e:
            logger.error("Failed to backfill %s for %s: %s", trade_date, ticker, e)

    logger.info("Backfill complete for %s: %d rows loaded", ticker, rows_loaded)
    return rows_loaded


def run_incremental_load() -> None:
    """Detect data gaps for all tickers and backfill missing dates from yfinance."""
    from scripts.setup_postgres import get_connection

    bucket = os.environ.get("AWS_BUCKET_NAME", "")
    conn = get_connection()

    total_rows = 0
    tickers_loaded = 0

    try:
        for ticker in TICKERS:
            missing = get_missing_dates(ticker, conn)
            if not missing:
                logger.info("No missing dates for %s — skipping", ticker)
                continue

            start = datetime.strptime(missing[0], "%Y/%m/%d").strftime("%Y-%m-%d")
            end = (datetime.strptime(missing[-1], "%Y/%m/%d") + timedelta(days=1)).strftime(
                "%Y-%m-%d"
            )

            rows = backfill_ticker(ticker, conn, bucket, start, end)
            total_rows += rows
            if rows > 0:
                tickers_loaded += 1
    finally:
        conn.close()

    logger.info(
        "Incremental load complete: %d total rows loaded across %d tickers",
        total_rows,
        tickers_loaded,
    )


if __name__ == "__main__":
    run_incremental_load()
