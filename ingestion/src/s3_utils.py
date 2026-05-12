"""S3 upload / download helpers for the raw data lake layer."""
import io
import logging
from datetime import date

import boto3
import pandas as pd

logger = logging.getLogger(__name__)


def _s3_key(prefix: str, target_date: date, filename: str = "stocks.parquet") -> str:
    return f"{prefix}/{target_date:%Y/%m/%d}/{filename}"


def upload_dataframe_to_s3(
    df: pd.DataFrame,
    bucket: str,
    prefix: str,
    target_date: date,
) -> str:
    """
    Serialise df as Parquet and upload to S3.

    Returns the full S3 key of the uploaded object.
    """
    if df.empty:
        logger.warning("Empty DataFrame — skipping S3 upload")
        return ""

    key = _s3_key(prefix, target_date)
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow", compression="snappy")
    buffer.seek(0)

    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=buffer.getvalue(),
        ContentType="application/octet-stream",
        Metadata={"source": "yfinance", "pipeline": "stock-price-pipeline"},
    )
    logger.info("Uploaded s3://%s/%s (%d rows)", bucket, key, len(df))
    return key


def download_dataframe_from_s3(bucket: str, key: str) -> pd.DataFrame:
    """Download a Parquet file from S3 and return as a DataFrame."""
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    buffer = io.BytesIO(response["Body"].read())
    df = pd.read_parquet(buffer, engine="pyarrow")
    logger.info("Downloaded s3://%s/%s (%d rows)", bucket, key, len(df))
    return df


def s3_key_for_date(prefix: str, target_date: date) -> str:
    """Return the expected S3 key for a given date (used by the load task)."""
    return _s3_key(prefix, target_date)
