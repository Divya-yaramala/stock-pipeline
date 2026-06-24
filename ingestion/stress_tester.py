import concurrent.futures
import datetime
import json
import logging
import random
import time

import boto3
import yfinance as yf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def stress_test_s3_uploads(bucket: str, num_files: int = 100, num_workers: int = 10) -> dict:
    s3 = boto3.client("s3")
    results = {"success": 0, "failure": 0}

    def upload_one(i):
        key = f"testing/stress/uploads/dummy_{i}.json"
        payload = json.dumps({"index": i, "data": "x" * 100})
        try:
            s3.put_object(Bucket=bucket, Key=key, Body=payload)
            return True
        except Exception:
            return False

    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(upload_one, i): i for i in range(num_files)}
        for idx, future in enumerate(concurrent.futures.as_completed(futures), 1):
            if future.result():
                results["success"] += 1
            else:
                results["failure"] += 1
            if idx % 10 == 0:
                logger.info(f"S3 uploads progress: {idx}/{num_files}")

    total_time = time.time() - start
    success_rate = results["success"] / num_files if num_files > 0 else 0
    files_per_second = results["success"] / total_time if total_time > 0 else 0
    logger.info(
        f"S3 stress test done: {files_per_second:.1f} files/sec, {success_rate:.1%} success"
    )
    return {
        "total_time": total_time,
        "files_per_second": files_per_second,
        "success_rate": success_rate,
        "num_files": num_files,
    }


def stress_test_api_calls(num_calls: int = 50, num_workers: int = 5) -> dict:
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    latencies = []
    results = {"success": 0, "failure": 0}

    def call_one(i):
        ticker = tickers[i % len(tickers)]
        t0 = time.time()
        try:
            yf.Ticker(ticker).history(period="1d")
            elapsed = (time.time() - t0) * 1000
            return True, elapsed
        except Exception:
            elapsed = (time.time() - t0) * 1000
            return False, elapsed

    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(call_one, i) for i in range(num_calls)]
        for idx, future in enumerate(concurrent.futures.as_completed(futures), 1):
            ok, lat = future.result()
            latencies.append(lat)
            if ok:
                results["success"] += 1
            else:
                results["failure"] += 1
            if idx % 10 == 0:
                logger.info(f"API calls progress: {idx}/{num_calls}")

    total_time = time.time() - start
    success_rate = results["success"] / num_calls if num_calls > 0 else 0
    calls_per_second = num_calls / total_time if total_time > 0 else 0
    avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0
    logger.info(
        f"API stress test done: {calls_per_second:.1f} calls/sec, "
        f"avg latency {avg_latency_ms:.0f}ms"
    )
    return {
        "total_time": total_time,
        "calls_per_second": calls_per_second,
        "success_rate": success_rate,
        "avg_latency_ms": avg_latency_ms,
        "num_calls": num_calls,
    }


def stress_test_data_processing(num_records: int = 1000) -> dict:
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    records = [
        {
            "ticker": random.choice(tickers),
            "price": round(random.uniform(50, 500), 2),
            "volume": random.randint(1000, 10_000_000),
            "date": datetime.date.today().isoformat(),
        }
        for _ in range(num_records)
    ]

    valid_count = 0
    start = time.time()
    for rec in records:
        if (
            rec.get("price") is not None
            and int(str(rec["price"])) > 0
            and rec.get("volume") is not None
            and int(str(rec["volume"])) >= 0
            and rec.get("ticker")
            and rec.get("date")
        ):
            valid_count += 1

    validation_time = time.time() - start
    records_per_second = num_records / validation_time if validation_time > 0 else 0
    quality_score = (valid_count / num_records * 100) if num_records > 0 else 0
    logger.info(
        f"Data processing stress test done: {records_per_second:.0f} records/sec, "
        f"quality {quality_score:.1f}%"
    )
    return {
        "records_per_second": records_per_second,
        "validation_time": validation_time,
        "quality_score": quality_score,
        "num_records": num_records,
        "valid_count": valid_count,
    }


def run_full_stress_test(bucket: str) -> dict:
    logger.info("Starting full stress test suite")
    s3_results = stress_test_s3_uploads(bucket, num_files=100, num_workers=10)
    api_results = stress_test_api_calls(num_calls=50, num_workers=5)
    processing_results = stress_test_data_processing(num_records=1000)

    combined = {
        "s3": s3_results,
        "api": api_results,
        "processing": processing_results,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }

    now = datetime.datetime.utcnow()
    key = f"testing/stress/{now.year:04d}/{now.month:02d}/{now.day:02d}/results.json"
    try:
        s3_client = boto3.client("s3")
        s3_client.put_object(Bucket=bucket, Key=key, Body=json.dumps(combined))
        logger.info(f"Stress test results saved to s3://{bucket}/{key}")
    except Exception as e:
        logger.error(f"Failed to save stress test results: {e}")

    logger.info(
        f"Full stress test complete — S3: {s3_results['files_per_second']:.1f} files/sec, "
        f"API: {api_results['calls_per_second']:.1f} calls/sec, "
        f"Processing: {processing_results['records_per_second']:.0f} records/sec"
    )
    return combined


if __name__ == "__main__":
    pass
