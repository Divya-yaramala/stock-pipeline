import json
import logging
import os
from datetime import datetime

import boto3
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def validate_stock_data(df: pd.DataFrame, ticker: str) -> dict:
    """Run 7 data-quality checks on a stock OHLCV DataFrame and return a validation report."""
    checks = {}

    checks["row_count"] = len(df) >= 1

    required_cols = {"open", "high", "low", "close", "volume"}
    present_cols = {c.lower() for c in df.columns}
    checks["required_columns"] = required_cols.issubset(present_cols)

    close_col = next((c for c in df.columns if c.lower() == "close"), None)
    if close_col:
        checks["no_nulls"] = bool(df[close_col].isna().sum() == 0)
        checks["price_positive"] = bool((df[close_col] > 0).all())
    else:
        checks["no_nulls"] = False
        checks["price_positive"] = False

    volume_col = next((c for c in df.columns if c.lower() == "volume"), None)
    checks["volume_positive"] = bool((df[volume_col] > 0).all()) if volume_col else False

    high_col = next((c for c in df.columns if c.lower() == "high"), None)
    low_col = next((c for c in df.columns if c.lower() == "low"), None)
    if high_col and low_col:
        checks["high_gte_low"] = bool((df[high_col] >= df[low_col]).all())
        if close_col:
            checks["close_in_range"] = bool(
                ((df[close_col] >= df[low_col]) & (df[close_col] <= df[high_col])).all()
            )
        else:
            checks["close_in_range"] = False
    else:
        checks["high_gte_low"] = False
        checks["close_in_range"] = False

    passed = all(checks.values())
    report = {
        "ticker": ticker,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "passed": passed,
        "checks": checks,
    }
    logger.info(
        "Validation for %s: %s | checks: %s",
        ticker,
        "PASSED" if passed else "FAILED",
        checks,
    )
    return report


def validate_anomaly_data(data: dict, ticker: str) -> dict:
    """Validate anomaly detection output dict and return a validation report."""
    checks = {}
    checks["has_is_anomaly_key"] = "is_anomaly" in data
    checks["has_anomaly_score_key"] = "anomaly_score" in data
    checks["valid_anomaly_value"] = isinstance(data.get("is_anomaly"), bool)

    passed = all(checks.values())
    report = {
        "ticker": ticker,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "passed": passed,
        "checks": checks,
    }
    logger.info(
        "Anomaly validation for %s: %s",
        ticker,
        "PASSED" if passed else "FAILED",
    )
    return report


def validate_price_event(event: dict) -> bool:
    """Validate a stock price event dict. Returns True if all required fields are present and valid."""
    required_keys = {"ticker", "price_usd", "timestamp", "volume"}
    if not required_keys.issubset(event.keys()):
        return False
    try:
        if float(event["price_usd"]) <= 0:
            return False
        if int(event["volume"]) < 0:
            return False
    except (TypeError, ValueError):
        return False
    return True


def save_validation_report(report: dict, ticker: str, bucket: str, date: str) -> bool:
    """Save a validation report JSON to S3 at processed/validation/YYYY/MM/DD/ticker.json."""
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        key = f"processed/validation/{date}/{ticker}.json"
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(report))
        logger.info("Validation report saved to s3://%s/%s", bucket, key)
        return True
    except Exception as e:
        logger.error("Failed to save validation report for %s: %s", ticker, e)
        return False


def run_validation() -> None:
    """Validate today's stock data for all tickers, save reports, and send failures to DLQ."""
    from ingestion.dead_letter_queue import send_to_dlq

    bucket = os.environ.get("AWS_BUCKET_NAME", "")
    date = datetime.now().strftime("%Y/%m/%d")
    s3 = boto3.client("s3", region_name=AWS_REGION)

    passed_count = 0
    failed_count = 0

    for ticker in TICKERS:
        key = f"raw/stocks/{date}/{ticker}.json"
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            raw = json.loads(response["Body"].read().decode("utf-8"))
            df = pd.DataFrame(raw)
            df.columns = [c.lower() for c in df.columns]

            report = validate_stock_data(df, ticker)
            save_validation_report(report, ticker, bucket, date)

            if report["passed"]:
                passed_count += 1
            else:
                failed_count += 1
                send_to_dlq(
                    error="Validation failed",
                    ticker=ticker,
                    step="validation",
                    payload=report,
                    bucket=bucket,
                )
        except Exception as e:
            logger.error("Error validating %s: %s", ticker, e)
            failed_count += 1
            send_to_dlq(
                error=str(e),
                ticker=ticker,
                step="validation",
                payload={},
                bucket=bucket,
            )

    logger.info("Validation complete: %d passed, %d failed", passed_count, failed_count)


if __name__ == "__main__":
    run_validation()
