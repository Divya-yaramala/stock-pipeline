import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def run_parallel_tasks(
    tasks: List[Dict[str, Any]],
    max_workers: int = 5,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(
                task["func"],
                *task.get("args", ()),
                **task.get("kwargs", {}),
            ): task
            for task in tasks
        }
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            start = time.time()
            try:
                result_value = future.result()
                duration = time.time() - start
                results.append(
                    {
                        "name": str(task["name"]),
                        "result": result_value,
                        "duration_seconds": round(duration, 4),
                        "status": "success",
                    }
                )
            except Exception as e:
                duration = time.time() - start
                results.append(
                    {
                        "name": str(task["name"]),
                        "result": None,
                        "duration_seconds": round(duration, 4),
                        "status": f"failed: {e}",
                    }
                )
    success = sum(1 for r in results if str(r["status"]) == "success")
    logger.info(f"Parallel tasks complete: {success}/{len(tasks)} succeeded")
    return results


def run_parallel_ticker_processing(
    tickers: List[str],
    process_func: Callable,
    max_workers: int = 5,
    **kwargs: Any,
) -> Dict[str, Any]:
    start_total = time.time()
    ticker_results: Dict[str, Any] = {}
    success_count = 0
    failed_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(process_func, ticker, **kwargs): ticker for ticker in tickers
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                ticker_results[ticker] = future.result()
                success_count += 1
            except Exception as e:
                ticker_results[ticker] = {"error": str(e)}
                failed_count += 1

    total_seconds = round(time.time() - start_total, 4)
    summary: Dict[str, Any] = {
        "results": ticker_results,
        "success_count": success_count,
        "failed_count": failed_count,
        "total_seconds": total_seconds,
    }
    logger.info(
        f"Parallel ticker processing: {success_count} success, "
        f"{failed_count} failed in {total_seconds}s"
    )
    return summary


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    chunks = [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]
    logger.info(f"Chunked {len(items)} items into {len(chunks)} chunks of size {chunk_size}")
    return chunks


def run_batch_s3_uploads(
    files: List[Dict[str, Any]],
    bucket: str,
    max_workers: int = 10,
) -> Dict[str, Any]:
    start_total = time.time()
    uploaded = 0
    failed = 0

    def _upload(file_entry: Dict[str, Any]) -> bool:
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        key = str(file_entry["key"])
        data = file_entry["data"]
        s3_client.put_object(Bucket=bucket, Key=key, Body=json.dumps(data, default=str))
        return True

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(_upload, f): f for f in files}
        for future in as_completed(future_to_file):
            try:
                future.result()
                uploaded += 1
            except Exception:
                failed += 1

    total_seconds = round(time.time() - start_total, 4)
    result: Dict[str, Any] = {
        "uploaded": uploaded,
        "failed": failed,
        "total_seconds": total_seconds,
    }
    logger.info(f"Batch S3 upload: {uploaded} uploaded, {failed} failed in {total_seconds}s")
    return result


def run_distributed_pipeline(
    tickers: List[str],
    pipeline_steps: List[str],
    bucket: str,
) -> Dict[str, Any]:
    start_total = time.time()
    steps_completed = 0

    def _run_step(ticker: str, step: str) -> Dict[str, Any]:
        return {"ticker": ticker, "step": step, "status": "completed"}

    tasks: List[Dict[str, Any]] = [
        {
            "name": f"{ticker}:{step}",
            "func": _run_step,
            "args": (ticker, step),
            "kwargs": {},
        }
        for ticker in tickers
        for step in pipeline_steps
    ]

    task_results = run_parallel_tasks(tasks, max_workers=5)
    steps_completed = sum(1 for r in task_results if str(r["status"]) == "success")

    total_seconds = round(time.time() - start_total, 4)
    summary: Dict[str, Any] = {
        "tickers_processed": len(tickers),
        "steps_completed": steps_completed,
        "total_seconds": total_seconds,
    }
    logger.info(
        f"Distributed pipeline: {len(tickers)} tickers, "
        f"{steps_completed} steps in {total_seconds}s"
    )
    return summary


if __name__ == "__main__":
    pass
