"""Load stock data from S3 into the PostgreSQL raw layer."""
import logging
from datetime import date

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

import config
from s3_utils import download_dataframe_from_s3, s3_key_for_date

logger = logging.getLogger(__name__)

_UPSERT_SQL = """
INSERT INTO raw.stock_prices (symbol, date, open, high, low, close, volume, s3_key)
VALUES %s
ON CONFLICT (symbol, date)
DO UPDATE SET
    open        = EXCLUDED.open,
    high        = EXCLUDED.high,
    low         = EXCLUDED.low,
    close       = EXCLUDED.close,
    volume      = EXCLUDED.volume,
    s3_key      = EXCLUDED.s3_key,
    _loaded_at  = CURRENT_TIMESTAMP;
"""


def _get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=config.WAREHOUSE_HOST,
        port=config.WAREHOUSE_PORT,
        user=config.WAREHOUSE_USER,
        password=config.WAREHOUSE_PASSWORD,
        dbname=config.WAREHOUSE_DB,
    )


def load_from_s3_to_postgres(
    bucket: str,
    prefix: str,
    target_date: date,
) -> int:
    """
    Download the Parquet file for target_date from S3 and upsert into raw.stock_prices.

    Returns the number of rows loaded.
    """
    key = s3_key_for_date(prefix, target_date)
    logger.info("Loading s3://%s/%s → raw.stock_prices", bucket, key)

    df = download_dataframe_from_s3(bucket, key)
    if df.empty:
        logger.warning("Parquet file is empty — nothing to load")
        return 0

    rows = [
        (
            row["symbol"],
            row["date"],
            float(row["open"]) if pd.notna(row["open"]) else None,
            float(row["high"]) if pd.notna(row["high"]) else None,
            float(row["low"]) if pd.notna(row["low"]) else None,
            float(row["close"]),
            int(row["volume"]) if pd.notna(row["volume"]) else None,
            key,
        )
        for _, row in df.iterrows()
    ]

    with _get_connection() as conn, conn.cursor() as cur:
        execute_values(cur, _UPSERT_SQL, rows)
        conn.commit()

    logger.info("Upserted %d row(s) into raw.stock_prices", len(rows))
    return len(rows)


def load_dataframe_to_postgres(df: pd.DataFrame, s3_key: str = "") -> int:
    """Upsert an in-memory DataFrame directly (used when S3 write is skipped)."""
    if df.empty:
        return 0

    rows = [
        (
            row["symbol"],
            row["date"],
            float(row["open"]) if pd.notna(row["open"]) else None,
            float(row["high"]) if pd.notna(row["high"]) else None,
            float(row["low"]) if pd.notna(row["low"]) else None,
            float(row["close"]),
            int(row["volume"]) if pd.notna(row["volume"]) else None,
            s3_key,
        )
        for _, row in df.iterrows()
    ]

    with _get_connection() as conn, conn.cursor() as cur:
        execute_values(cur, _UPSERT_SQL, rows)
        conn.commit()

    logger.info("Upserted %d row(s) directly into raw.stock_prices", len(rows))
    return len(rows)
