"""Performance benchmarker — measures S3, data processing, and function latencies."""

import json
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def benchmark_function(
    func: Callable,
    args: tuple = (),
    kwargs: dict = {},
    runs: int = 10,
) -> Dict[str, float]:
    """Run func N times and return latency statistics in milliseconds."""
    durations: List[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        func(*args, **kwargs)
        durations.append((time.perf_counter() - start) * 1000.0)

    durations.sort()
    avg_ms = sum(durations) / len(durations)
    min_ms = durations[0]
    max_ms = durations[-1]
    p95_idx = max(0, int(len(durations) * 0.95) - 1)
    p95_ms = durations[p95_idx]

    result: Dict[str, float] = {
        "avg_ms": round(avg_ms, 3),
        "min_ms": round(min_ms, 3),
        "max_ms": round(max_ms, 3),
        "p95_ms": round(p95_ms, 3),
    }
    logger.info(
        "Benchmark %s: avg=%.1f ms, p95=%.1f ms",
        func.__name__ if hasattr(func, "__name__") else "fn",
        avg_ms,
        p95_ms,
    )
    return result


def benchmark_s3_operations(bucket: str) -> Dict[str, Any]:
    """Benchmark put_object, get_object, and list_objects_v2 against a real S3 bucket."""
    s3 = boto3.client("s3")
    test_key = "benchmarks/test_object.json"
    test_body = json.dumps({"benchmark": True}).encode("utf-8")
    runs = 5

    put_times: List[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        try:
            s3.put_object(Bucket=bucket, Key=test_key, Body=test_body)
        except Exception:
            pass
        put_times.append((time.perf_counter() - start) * 1000.0)

    get_times: List[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        try:
            s3.get_object(Bucket=bucket, Key=test_key)
        except Exception:
            pass
        get_times.append((time.perf_counter() - start) * 1000.0)

    list_times: List[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        try:
            s3.list_objects_v2(Bucket=bucket, Prefix="benchmarks/", MaxKeys=10)
        except Exception:
            pass
        list_times.append((time.perf_counter() - start) * 1000.0)

    put_avg = round(sum(put_times) / len(put_times), 3)
    get_avg = round(sum(get_times) / len(get_times), 3)
    list_avg = round(sum(list_times) / len(list_times), 3)

    result: Dict[str, Any] = {
        "put_avg_ms": put_avg,
        "get_avg_ms": get_avg,
        "list_avg_ms": list_avg,
        "runs": runs,
    }
    logger.info("S3 benchmark: put=%.1f ms, get=%.1f ms, list=%.1f ms", put_avg, get_avg, list_avg)
    return result


def benchmark_data_processing(num_records: int = 1000) -> Dict[str, Any]:
    """Benchmark validation and feature engineering on dummy stock records."""
    records: List[Dict[str, Any]] = [
        {
            "ticker": "AAPL",
            "trade_date": "2026-01-01",
            "open_price": 150.0 + i * 0.01,
            "high_price": 155.0 + i * 0.01,
            "low_price": 148.0 + i * 0.01,
            "close_price": 152.0 + i * 0.01,
            "volume": 1000000 + i,
        }
        for i in range(num_records)
    ]

    start = time.perf_counter()

    validated = [
        r for r in records if float(str(r["close_price"])) > 0 and int(str(r["volume"])) > 0
    ]

    features = [
        {
            "ticker": str(r["ticker"]),
            "price_range": float(str(r["high_price"])) - float(str(r["low_price"])),
            "price_change": float(str(r["close_price"])) - float(str(r["open_price"])),
        }
        for r in validated
    ]

    _ = [
        {"ticker": str(f["ticker"]), "anomaly_score": abs(float(str(f["price_change"])) / 5.0)}
        for f in features
    ]

    elapsed = time.perf_counter() - start
    rps = round(num_records / elapsed, 1) if elapsed > 0 else 0.0

    result: Dict[str, Any] = {
        "records_per_second": rps,
        "total_seconds": round(elapsed, 4),
        "num_records": num_records,
    }
    logger.info("Data processing: %d records in %.4f s (%.0f rec/s)", num_records, elapsed, rps)
    return result


def compare_benchmarks(
    baseline: Dict[str, Any],
    current: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare current benchmark vs baseline. Flags >20% slower as regression."""
    regressions: List[Dict[str, Any]] = []
    improvements: List[Dict[str, Any]] = []
    unchanged: List[str] = []

    for key in baseline:
        if key not in current:
            continue
        base_val = float(str(baseline[key]))
        curr_val = float(str(current[key]))
        if base_val == 0:
            continue
        pct_change = round((curr_val - base_val) / base_val * 100.0, 1)
        entry: Dict[str, Any] = {
            "metric": key,
            "baseline": base_val,
            "current": curr_val,
            "pct_change": pct_change,
        }
        if pct_change > 20.0:
            regressions.append(entry)
        elif pct_change < -10.0:
            improvements.append(entry)
        else:
            unchanged.append(key)

    result: Dict[str, Any] = {
        "regressions": regressions,
        "improvements": improvements,
        "unchanged": unchanged,
    }
    logger.info(
        "Benchmark comparison: %d regressions, %d improvements",
        len(regressions),
        len(improvements),
    )
    return result


def run_benchmark_suite(bucket: str) -> Dict[str, Any]:
    """Run all benchmarks, save results to S3, and return combined dict."""
    s3 = boto3.client("s3")
    today = datetime.utcnow().strftime("%Y/%m/%d")

    processing = benchmark_data_processing(num_records=1000)
    s3_ops = benchmark_s3_operations(bucket)

    results: Dict[str, Any] = {
        "data_processing": processing,
        "s3_operations": s3_ops,
        "run_date": today,
        "generated_at": datetime.utcnow().isoformat(),
    }

    key = f"reports/benchmarks/{today}/results.json"
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(results, indent=2),
            ContentType="application/json",
        )
        logger.info("Benchmark results saved to s3://%s/%s", bucket, key)
    except Exception as exc:
        logger.warning("Could not save benchmark results: %s", exc)

    logger.info("Benchmark Suite Complete")
    return results


if __name__ == "__main__":
    pass
