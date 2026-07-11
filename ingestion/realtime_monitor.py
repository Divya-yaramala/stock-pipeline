import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

MONITOR_CHECKS: List[Dict[str, Any]] = [
    {"check_id": "M001", "name": "api_availability", "interval_seconds": 300},
    {"check_id": "M002", "name": "data_freshness", "interval_seconds": 3600},
    {"check_id": "M003", "name": "pipeline_lag", "interval_seconds": 600},
    {"check_id": "M004", "name": "error_rate", "interval_seconds": 900},
    {"check_id": "M005", "name": "resource_usage", "interval_seconds": 300},
]


def check_api_availability(ticker: str) -> Dict[str, Any]:
    start = time.monotonic()
    try:
        import yfinance as yf

        info = yf.Ticker(str(ticker)).fast_info
        _ = float(str(info.last_price))
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        logger.info("API availability for %s: ok (%.1f ms)", ticker, latency_ms)
        return {"available": True, "latency_ms": latency_ms, "ticker": ticker}
    except Exception as e:
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        logger.warning("API availability for %s: failed — %s", ticker, e)
        return {"available": False, "latency_ms": latency_ms, "ticker": ticker}


def check_pipeline_lag(bucket: str, ticker: str) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    today = datetime.utcnow().strftime("%Y/%m/%d")
    prefix = f"raw/stocks/{today}/{ticker}"
    lag_minutes = 999.0
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        contents = response.get("Contents", [])
        if contents:
            latest = max(contents, key=lambda o: str(o.get("LastModified", "")))
            lm = latest.get("LastModified")
            if lm:
                if hasattr(lm, "replace"):
                    lm_str = str(lm)
                    lm_dt = datetime.fromisoformat(lm_str.replace("Z", "+00:00"))
                    now_dt = datetime.now(lm_dt.tzinfo)
                    lag_minutes = round((now_dt - lm_dt).total_seconds() / 60, 1)
                else:
                    lag_minutes = round(
                        (datetime.utcnow() - lm.replace(tzinfo=None)).total_seconds() / 60, 1
                    )
    except Exception as e:
        logger.error("Pipeline lag check failed for %s: %s", ticker, e)

    acceptable = lag_minutes < 60.0
    logger.info("Pipeline lag for %s: %.1f min (acceptable=%s)", ticker, lag_minutes, acceptable)
    return {"lag_minutes": lag_minutes, "acceptable": acceptable, "ticker": ticker}


def check_error_rate(bucket: str, date: str) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    date_path = date.replace("-", "/")
    error_count = 0
    total_count = 0

    try:
        dlq_prefix = f"dead_letter_queue/{date_path}/"
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=dlq_prefix)
        error_count = int(str(resp.get("KeyCount", 0)))
    except Exception:
        pass

    try:
        mon_prefix = f"monitoring/pipeline/{date_path}/"
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=mon_prefix)
        total_count = max(int(str(resp.get("KeyCount", 0))), 1)
    except Exception:
        total_count = 1

    error_rate_pct = round((error_count / total_count) * 100, 2)
    acceptable = error_rate_pct < 5.0
    logger.info("Error rate for %s: %.2f%% (acceptable=%s)", date, error_rate_pct, acceptable)
    return {"error_rate_pct": error_rate_pct, "acceptable": acceptable}


def record_monitor_result(check_id: str, result: Dict[str, Any], bucket: str) -> bool:
    now = datetime.utcnow()
    timestamp = now.strftime("%Y%m%dT%H%M%S")
    key = (
        f"monitoring/realtime/{now.year}/{now.month:02d}/{now.day:02d}/"
        f"{check_id}_{timestamp}.json"
    )
    payload = {"check_id": check_id, "recorded_at": now.isoformat(), **result}
    try:
        s3 = boto3.client("s3")
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload))
        return True
    except Exception as e:
        logger.error("Failed to record monitor result %s: %s", check_id, e)
        return False


def run_monitor_cycle(
    bucket: str,
    tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if tickers is None:
        tickers = DEFAULT_TICKERS

    results: List[Dict[str, Any]] = []
    issues_found = 0
    date = datetime.utcnow().strftime("%Y-%m-%d")

    for ticker in tickers:
        api_result = check_api_availability(str(ticker))
        record_monitor_result("M001", api_result, bucket)
        results.append({"check": "api_availability", "ticker": ticker, **api_result})
        if not api_result.get("available", True):
            issues_found += 1

        lag_result = check_pipeline_lag(bucket, str(ticker))
        record_monitor_result("M003", lag_result, bucket)
        results.append({"check": "pipeline_lag", "ticker": ticker, **lag_result})
        if not lag_result.get("acceptable", True):
            issues_found += 1

    error_result = check_error_rate(bucket, date)
    record_monitor_result("M004", error_result, bucket)
    results.append({"check": "error_rate", **error_result})
    if not error_result.get("acceptable", True):
        issues_found += 1

    summary: Dict[str, Any] = {
        "checks_run": len(results),
        "issues_found": issues_found,
        "results": results,
    }
    logger.info(
        "Monitor cycle complete: %d checks run, %d issues found",
        len(results),
        issues_found,
    )
    return summary


if __name__ == "__main__":
    pass
