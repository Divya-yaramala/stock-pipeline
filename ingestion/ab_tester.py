import json
import logging
from datetime import datetime
from typing import Any, Dict, List

import boto3
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_ab_experiment(
    experiment_name: str,
    model_a: str,
    model_b: str,
    traffic_split: float = 0.5,
    bucket: str = "",
) -> str:
    experiment_id = f"exp_{experiment_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    config: Dict[str, Any] = {
        "experiment_id": experiment_id,
        "experiment_name": experiment_name,
        "model_a": model_a,
        "model_b": model_b,
        "traffic_split": traffic_split,
        "status": "running",
        "created_at": datetime.utcnow().isoformat(),
    }
    s3 = boto3.client("s3")
    key = f"models/experiments/{experiment_name}/config.json"
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(config),
            ContentType="application/json",
        )
        logger.info("A/B experiment created: %s", experiment_id)
    except Exception as e:
        logger.error("Failed to save experiment config: %s", e)
    return experiment_id


def assign_model(
    experiment_id: str,
    ticker: str,
    bucket: str,
) -> str:
    hash_val = hash(f"{experiment_id}:{ticker}") % 100
    assigned = "model_a" if hash_val < 50 else "model_b"
    logger.info("Assigned %s to %s for experiment %s", assigned, ticker, experiment_id)
    return assigned


def record_ab_result(
    experiment_id: str,
    model_assigned: str,
    ticker: str,
    prediction: float,
    actual: float,
    bucket: str,
) -> bool:
    s3 = boto3.client("s3")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    key = f"models/experiments/{experiment_id}/results/{ticker}_{timestamp}.json"
    result: Dict[str, Any] = {
        "experiment_id": experiment_id,
        "model_assigned": model_assigned,
        "ticker": ticker,
        "prediction": prediction,
        "actual": actual,
        "error": abs(prediction - actual),
        "recorded_at": datetime.utcnow().isoformat(),
    }
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(result),
            ContentType="application/json",
        )
        logger.info("A/B result recorded for %s model=%s", ticker, model_assigned)
        return True
    except Exception as e:
        logger.error("Failed to record A/B result: %s", e)
        return False


def analyze_ab_results(
    experiment_id: str,
    bucket: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    prefix = f"models/experiments/{experiment_id}/results/"
    model_a_errors: List[float] = []
    model_b_errors: List[float] = []

    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                response = s3.get_object(Bucket=bucket, Key=str(obj["Key"]))
                record: Dict[str, Any] = json.loads(response["Body"].read().decode("utf-8"))
                error = float(str(record.get("error", 0.0)))
                if str(record.get("model_assigned", "")) == "model_a":
                    model_a_errors.append(error)
                else:
                    model_b_errors.append(error)
    except Exception as e:
        logger.error("Failed to load A/B results: %s", e)

    model_a_mae = float(np.mean(model_a_errors)) if model_a_errors else 0.0
    model_b_mae = float(np.mean(model_b_errors)) if model_b_errors else 0.0

    winner = "model_a" if model_a_mae <= model_b_mae else "model_b"

    total = len(model_a_errors) + len(model_b_errors)
    if total < 10:
        confidence = "low"
    elif total < 30:
        confidence = "medium"
    else:
        confidence = "high"

    results: Dict[str, Any] = {
        "experiment_id": experiment_id,
        "winner": winner,
        "model_a_mae": model_a_mae,
        "model_b_mae": model_b_mae,
        "model_a_samples": len(model_a_errors),
        "model_b_samples": len(model_b_errors),
        "confidence": confidence,
    }
    logger.info("A/B test results: winner=%s confidence=%s", winner, confidence)
    return results


def conclude_experiment(
    experiment_id: str,
    bucket: str,
) -> Dict[str, Any]:
    analysis = analyze_ab_results(experiment_id, bucket)
    analysis["status"] = "concluded"
    analysis["concluded_at"] = datetime.utcnow().isoformat()

    s3 = boto3.client("s3")
    key = f"models/experiments/{experiment_id}/conclusion.json"
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(analysis),
            ContentType="application/json",
        )
        logger.info("Experiment %s concluded: winner=%s", experiment_id, analysis["winner"])
    except Exception as e:
        logger.error("Failed to save conclusion: %s", e)

    return analysis


if __name__ == "__main__":
    pass
