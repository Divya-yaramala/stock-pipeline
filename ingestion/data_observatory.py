import json
import logging
import os
from datetime import datetime, timezone

import boto3
import pandas as pd

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

REQUIRED_PATHS = [
    "raw/stocks/{date}/{ticker}.json",
    "processed/anomalies/{date}/{ticker}.json",
    "processed/predictions/{date}/{ticker}.json",
    "processed/insights/{date}/{ticker}.json",
    "processed/sentiment/{date}/{ticker}.json",
]


def check_data_freshness(bucket: str, ticker: str) -> dict:
    s3 = boto3.client("s3")
    key = f"raw/stocks/latest/{ticker}.json"
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(response["Body"].read().decode("utf-8"))
        last_updated = data.get("timestamp", data.get("ingested_at", ""))
        if last_updated:
            last_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            hours_since = (now - last_dt).total_seconds() / 3600.0
        else:
            hours_since = 999.0
            last_updated = "unknown"
        is_fresh = hours_since < 25.0
        status = "FRESH" if is_fresh else "STALE"
        logger.info("%s data freshness: %s (%.1fh ago)", ticker, status, hours_since)
        return {
            "ticker": ticker,
            "last_updated": last_updated,
            "hours_since_update": round(hours_since, 2),
            "is_fresh": is_fresh,
        }
    except Exception as e:
        logger.warning("Could not check freshness for %s: %s", ticker, e)
        return {
            "ticker": ticker,
            "last_updated": "unknown",
            "hours_since_update": 999.0,
            "is_fresh": False,
        }


def check_data_completeness(bucket: str, ticker: str, date: str) -> dict:
    s3 = boto3.client("s3")
    path_date = date.replace("-", "/")
    missing = []

    for path_template in REQUIRED_PATHS:
        key = path_template.format(date=path_date, ticker=ticker)
        try:
            s3.head_object(Bucket=bucket, Key=key)
        except Exception:
            missing.append(key)

    present = len(REQUIRED_PATHS) - len(missing)
    completeness_pct = round(present / len(REQUIRED_PATHS) * 100, 1)
    logger.info("%s completeness on %s: %.1f%% (%d/%d files)", ticker, date, completeness_pct, present, len(REQUIRED_PATHS))
    return {
        "ticker": ticker,
        "date": date,
        "completeness_pct": completeness_pct,
        "missing": missing,
    }


def check_data_consistency(bucket: str, ticker: str, date: str) -> dict:
    s3 = boto3.client("s3")
    path_date = date.replace("-", "/")
    issues = []

    try:
        price_key = f"raw/stocks/{path_date}/{ticker}.json"
        price_resp = s3.get_object(Bucket=bucket, Key=price_key)
        price_data = json.loads(price_resp["Body"].read().decode("utf-8"))
        if isinstance(price_data, list) and price_data:
            price_record = price_data[0]
        else:
            price_record = price_data
    except Exception as e:
        issues.append(f"Cannot load price data: {e}")
        return {"ticker": ticker, "is_consistent": False, "issues": issues}

    try:
        anomaly_key = f"processed/anomalies/{path_date}/{ticker}.json"
        anomaly_resp = s3.get_object(Bucket=bucket, Key=anomaly_key)
        anomaly_data = json.loads(anomaly_resp["Body"].read().decode("utf-8"))
        if isinstance(anomaly_data, list) and anomaly_data:
            anomaly_record = anomaly_data[0]
        else:
            anomaly_record = anomaly_data
    except Exception as e:
        issues.append(f"Cannot load anomaly data: {e}")
        return {"ticker": ticker, "is_consistent": False, "issues": issues}

    anomaly_ticker = anomaly_record.get("ticker", "")
    if anomaly_ticker and anomaly_ticker != ticker:
        issues.append(f"Ticker mismatch: price={ticker}, anomaly={anomaly_ticker}")

    anomaly_date = anomaly_record.get("trade_date", anomaly_record.get("date", ""))
    price_date = price_record.get("date", price_record.get("trade_date", ""))
    if anomaly_date and price_date and anomaly_date != price_date:
        issues.append(f"Date mismatch: price={price_date}, anomaly={anomaly_date}")

    is_consistent = len(issues) == 0
    logger.info("%s consistency on %s: %s", ticker, date, "OK" if is_consistent else f"{len(issues)} issue(s)")
    return {"ticker": ticker, "is_consistent": is_consistent, "issues": issues}


def calculate_health_score(freshness: dict, completeness: dict, consistency: dict) -> float:
    freshness_score = 1.0 if freshness.get("is_fresh", False) else 0.0
    completeness_score = completeness.get("completeness_pct", 0.0) / 100.0
    consistency_score = 1.0 if consistency.get("is_consistent", False) else 0.0

    score = (freshness_score * 0.30 + completeness_score * 0.50 + consistency_score * 0.20) * 100
    score = round(score, 2)
    logger.info(
        "Health score for %s: %.1f (fresh=%.0f%% complete=%.0f%% consistent=%.0f%%)",
        freshness.get("ticker", ""),
        score,
        freshness_score * 100,
        completeness_score * 100,
        consistency_score * 100,
    )
    return score


def run_observability_check(bucket: str) -> dict:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    results = {}
    healthy = 0
    needs_attention = 0

    for ticker in TICKERS:
        freshness = check_data_freshness(bucket, ticker)
        completeness = check_data_completeness(bucket, ticker, date)
        consistency = check_data_consistency(bucket, ticker, date)
        health_score = calculate_health_score(freshness, completeness, consistency)

        results[ticker] = {
            "freshness": freshness,
            "completeness": completeness,
            "consistency": consistency,
            "health_score": health_score,
        }

        if health_score >= 80:
            healthy += 1
        else:
            needs_attention += 1

    logger.info("Observability check complete: %d tickers healthy, %d need attention", healthy, needs_attention)
    return {
        "date": date,
        "tickers": results,
        "summary": {"healthy": healthy, "needs_attention": needs_attention},
    }


if __name__ == "__main__":
    _bucket = os.getenv("AWS_BUCKET_NAME", "")
    pass
