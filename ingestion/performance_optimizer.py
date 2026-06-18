import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from functools import wraps

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def timer_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{func.__name__} completed in {duration:.3f}s")
        return result

    return wrapper


def batch_processor(items: list, batch_size: int, process_func, *args) -> list:
    results = []
    total_batches = (len(items) + batch_size - 1) // batch_size
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        batch_num = i // batch_size + 1
        batch_result = process_func(batch, *args)
        if isinstance(batch_result, list):
            results.extend(batch_result)
        logger.info(f"Batch {batch_num} of {total_batches} processed")
    return results


def parallel_fetch(tickers: list, fetch_func, max_workers: int = 5) -> dict:
    results = {}
    start = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {executor.submit(fetch_func, ticker): ticker for ticker in tickers}
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                results[ticker] = future.result()
            except Exception as e:
                logger.error(f"Fetch failed for {ticker}: {e}")
                results[ticker] = None
    parallel_time = time.time() - start
    sequential_estimate = parallel_time * max_workers
    time_saved = sequential_estimate - parallel_time
    logger.info(
        f"Parallel fetch complete in {parallel_time:.3f}s "
        f"(estimated time saved vs sequential: {time_saved:.3f}s)"
    )
    return results


def optimize_s3_uploads(files: list, bucket: str, prefix: str) -> int:
    s3 = boto3.client("s3")
    uploaded = 0
    start = time.time()

    def upload_file(file_path: str) -> bool:
        key = f"{prefix}/{os.path.basename(file_path)}"
        try:
            s3.upload_file(file_path, bucket, key)
            return True
        except Exception as e:
            logger.error(f"Upload failed for {file_path}: {e}")
            return False

    with ThreadPoolExecutor(max_workers=min(len(files), 10)) as executor:
        futures = [executor.submit(upload_file, f) for f in files]
        for future in as_completed(futures):
            if future.result():
                uploaded += 1

    duration = time.time() - start
    logger.info(f"Uploaded {uploaded}/{len(files)} files in {duration:.3f}s")
    return uploaded


def run_performance_benchmark() -> dict:
    import yfinance as yf

    def fetch_ticker(ticker: str) -> dict:
        info = yf.Ticker(ticker).fast_info
        return {"ticker": ticker, "price": getattr(info, "last_price", None)}

    seq_start = time.time()
    for ticker in TICKERS:
        fetch_ticker(ticker)
    seq_time = time.time() - seq_start

    par_start = time.time()
    parallel_fetch(TICKERS, fetch_ticker)
    par_time = time.time() - par_start

    speedup = seq_time / par_time if par_time > 0 else 1.0
    benchmark = {
        "sequential_time_seconds": round(seq_time, 3),
        "parallel_time_seconds": round(par_time, 3),
        "speedup_factor": round(speedup, 2),
        "tickers": TICKERS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(f"Benchmark complete — speedup factor: {speedup:.2f}x")
    return benchmark


if __name__ == "__main__":
    pass
