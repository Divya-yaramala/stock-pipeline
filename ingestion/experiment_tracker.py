import json
import logging
import os
from datetime import datetime

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def start_experiment(
    experiment_name: str,
    model_name: str,
    params: dict,
    bucket: str,
) -> str:
    """
    Start a new experiment run and save the record to S3.

    Args:
        experiment_name: Name of the experiment.
        model_name: Name of the model being tested.
        params: Dictionary of experiment hyperparameters.
        bucket: S3 bucket name.

    Returns:
        run_id string for the new experiment run.
    """
    now = datetime.utcnow()
    run_id = f"{experiment_name}_{now.strftime('%Y%m%d_%H%M%S_%f')}"
    date_path = now.strftime("%Y/%m/%d")

    record = {
        "run_id": run_id,
        "experiment_name": experiment_name,
        "model_name": model_name,
        "params": params,
        "metrics": {},
        "started_at": now.isoformat(),
        "status": "running",
    }

    key = f"experiments/{date_path}/{experiment_name}/{run_id}.json"
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(record),
        ContentType="application/json",
    )
    logger.info("Started experiment %s run %s", experiment_name, run_id)
    return run_id


def _find_experiment_key(run_id: str, bucket: str) -> str:
    """Scan S3 for the object key containing the given run_id."""
    s3 = boto3.client("s3")
    response = s3.list_objects_v2(Bucket=bucket, Prefix="experiments/")
    for obj in response.get("Contents", []):
        if run_id in obj["Key"]:
            return obj["Key"]
    raise FileNotFoundError(f"Experiment run {run_id} not found in bucket {bucket}")


def log_metrics(
    run_id: str,
    metrics: dict,
    bucket: str,
) -> bool:
    """
    Update an experiment run record with evaluation metrics.

    Args:
        run_id: Unique run identifier returned by start_experiment.
        metrics: Dictionary of metric name → value pairs.
        bucket: S3 bucket name.

    Returns:
        True on success, False on failure.
    """
    try:
        key = _find_experiment_key(run_id, bucket)
        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket, Key=key)
        record = json.loads(response["Body"].read().decode("utf-8"))
        record["metrics"].update(metrics)
        record["metrics_logged_at"] = datetime.utcnow().isoformat()
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(record),
            ContentType="application/json",
        )
        logger.info("Logged metrics for run %s: %s", run_id, metrics)
        return True
    except Exception as e:
        logger.error("Failed to log metrics for run %s: %s", run_id, e)
        return False


def end_experiment(
    run_id: str,
    status: str,
    bucket: str,
) -> bool:
    """
    Mark an experiment run as completed or failed.

    Args:
        run_id: Unique run identifier returned by start_experiment.
        status: Final status — "completed" or "failed".
        bucket: S3 bucket name.

    Returns:
        True on success, False on failure.
    """
    try:
        key = _find_experiment_key(run_id, bucket)
        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket, Key=key)
        record = json.loads(response["Body"].read().decode("utf-8"))
        record["status"] = status
        record["ended_at"] = datetime.utcnow().isoformat()
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(record),
            ContentType="application/json",
        )
        logger.info("Ended experiment run %s with status %s", run_id, status)
        return True
    except Exception as e:
        logger.error("Failed to end experiment run %s: %s", run_id, e)
        return False


def get_best_experiment(
    experiment_name: str,
    metric: str,
    bucket: str,
) -> dict:
    """
    Find the experiment run with the best (highest) value for a given metric.

    Args:
        experiment_name: Name of the experiment.
        metric: Metric name to rank by.
        bucket: S3 bucket name.

    Returns:
        Experiment record dict for the best run, or empty dict if none found.
    """
    s3 = boto3.client("s3")
    response = s3.list_objects_v2(Bucket=bucket, Prefix="experiments/")

    best = {}
    best_value = None

    for obj in response.get("Contents", []):
        if experiment_name not in obj["Key"]:
            continue
        record_response = s3.get_object(Bucket=bucket, Key=obj["Key"])
        record = json.loads(record_response["Body"].read().decode("utf-8"))
        value = record.get("metrics", {}).get(metric)
        if value is not None:
            if best_value is None or value > best_value:
                best_value = value
                best = record

    if best:
        logger.info(
            "Best experiment for %s on %s: run %s (value=%.4f)",
            experiment_name,
            metric,
            best.get("run_id"),
            best_value,
        )
    return best


if __name__ == "__main__":
    _default_bucket = os.getenv("AWS_S3_BUCKET", "")
