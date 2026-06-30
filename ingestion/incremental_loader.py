import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3
import yfinance as yf

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def get_last_loaded_date(ticker: str, bucket: str) -> Optional[str]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    key = f"watermarks/{ticker}.json"
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(response["Body"].read().decode("utf-8"))
        date_str = str(data["last_loaded_date"])
        logger.info("Last loaded date for %s: %s", ticker, date_str)
        return date_str
    except Exception:
        logger.info("No watermark found for %s", ticker)
        return None


def save_watermark(ticker: str, date: str, bucket: str) -> bool:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    key = f"watermarks/{ticker}.json"
    payload = json.dumps({"last_loaded_date": date})
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=payload)
        logger.info("Saved watermark for %s: %s", ticker, date)
        return True
    except Exception as e:
        logger.error("Failed to save watermark for %s: %s", ticker, e)
        return False


def detect_data_gaps(
    ticker: str,
    bucket: str,
    start_date: str,
    end_date: str,
) -> List[str]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    missing: List[str] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            date_slash = current.strftime("%Y/%m/%d")
            key = f"raw/stocks/{date_slash}/{ticker}.json"
            try:
                s3.head_object(Bucket=bucket, Key=key)
            except Exception:
                missing.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    logger.info(
        "Detected %d gaps for %s between %s and %s",
        len(missing),
        ticker,
        start_date,
        end_date,
    )
    return missing


def load_incremental_data(
    ticker: str,
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    df = yf.download(ticker, start=start_date, end=end_date, progress=False)
    result: Dict[str, Any] = {}

    if df.empty:
        logger.info("No data from yfinance for %s between %s and %s", ticker, start_date, end_date)
        return result

    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)
    df.columns = [col.lower() for col in df.columns]

    for date_idx, row in df.iterrows():
        trade_date = date_idx.strftime("%Y-%m-%d")
        result[trade_date] = {
            "open": float(str(row.get("open") or 0)),
            "high": float(str(row.get("high") or 0)),
            "low": float(str(row.get("low") or 0)),
            "close": float(str(row.get("close") or 0)),
            "volume": int(str(int(row.get("volume") or 0))),
        }

    logger.info("Loaded %d records for %s", len(result), ticker)
    return result


def run_incremental_load(tickers: List[str], bucket: str) -> Dict[str, Any]:
    tickers_updated = 0
    total_records = 0
    gaps_filled = 0

    for ticker in tickers:
        last_date = get_last_loaded_date(ticker, bucket)
        start_date = (
            last_date if last_date else (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        )
        end_date = datetime.now().strftime("%Y-%m-%d")

        gaps = detect_data_gaps(ticker, bucket, start_date, end_date)
        if not gaps:
            logger.info("No gaps found for %s", ticker)
            continue

        data = load_incremental_data(ticker, gaps[0], gaps[-1])
        total_records += len(data)
        gaps_filled += len(gaps)

        if data:
            new_watermark = max(data.keys())
            save_watermark(ticker, new_watermark, bucket)
            tickers_updated += 1

    result: Dict[str, Any] = {
        "tickers_updated": tickers_updated,
        "total_records": total_records,
        "gaps_filled": gaps_filled,
    }
    logger.info("Incremental load summary: %s", result)
    return result


if __name__ == "__main__":
    pass
