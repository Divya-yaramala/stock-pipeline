import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_experiment(
    name: str,
    description: str,
    variants: List[str],
    traffic_split: Optional[Dict[str, float]] = None,
    bucket: str = "",
) -> str:
    experiment_id = str(
        hashlib.md5(f"{name}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:12]
    )
    if traffic_split is None:
        equal_share = round(1.0 / len(variants), 4)
        traffic_split = {v: equal_share for v in variants}
    config: Dict[str, Any] = {
        "experiment_id": str(experiment_id),
        "name": str(name),
        "description": str(description),
        "variants": [str(v) for v in variants],
        "traffic_split": {str(k): float(v) for k, v in traffic_split.items()},
        "status": "running",
        "created_at": str(datetime.utcnow().isoformat()),
    }
    try:
        client = boto3.client("s3")
        client.put_object(
            Bucket=bucket,
            Key=f"experiments/{experiment_id}/config.json",
            Body=json.dumps(config, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Experiment created: %s (%s)", name, experiment_id)
    except Exception as e:
        logger.error("Failed to save experiment config: %s", str(e))
    return experiment_id


def get_variant(experiment_id: str, ticker: str, bucket: str) -> str:
    try:
        client = boto3.client("s3")
        response = client.get_object(Bucket=bucket, Key=f"experiments/{experiment_id}/config.json")
        config: Dict[str, Any] = json.loads(response["Body"].read().decode("utf-8"))
        variants: List[str] = [str(v) for v in config.get("variants", [])]
        if not variants:
            return "control"
        hash_val = int(hashlib.md5(f"{experiment_id}_{ticker}".encode()).hexdigest(), 16)
        variant = str(variants[hash_val % len(variants)])
        logger.info("Variant assigned: %s → %s (experiment: %s)", ticker, variant, experiment_id)
        return variant
    except Exception as e:
        logger.error("Failed to get variant: %s", str(e))
        return "control"


def record_experiment_outcome(
    experiment_id: str,
    variant: str,
    ticker: str,
    metric_name: str,
    metric_value: float,
    bucket: str,
) -> bool:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    outcome: Dict[str, Any] = {
        "experiment_id": str(experiment_id),
        "variant": str(variant),
        "ticker": str(ticker),
        "metric_name": str(metric_name),
        "metric_value": float(metric_value),
        "recorded_at": str(datetime.utcnow().isoformat()),
    }
    try:
        client = boto3.client("s3")
        client.put_object(
            Bucket=bucket,
            Key=f"experiments/{experiment_id}/outcomes/{ticker}_{timestamp}.json",
            Body=json.dumps(outcome, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        return True
    except Exception as e:
        logger.error("Failed to record outcome: %s", str(e))
        return False


def analyze_experiment(experiment_id: str, bucket: str) -> Dict[str, Any]:
    try:
        client = boto3.client("s3")
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=f"experiments/{experiment_id}/outcomes/")
        by_variant: Dict[str, List[float]] = {}
        sample_count = 0
        for page in pages:
            for obj in page.get("Contents", []):
                resp = client.get_object(Bucket=bucket, Key=str(obj["Key"]))
                outcome: Dict[str, Any] = json.loads(resp["Body"].read().decode("utf-8"))
                v = str(outcome.get("variant", "unknown"))
                val = float(str(outcome.get("metric_value", 0.0)))
                by_variant.setdefault(v, []).append(val)
                sample_count += 1
        avg_by_variant: Dict[str, Any] = {
            v: float(sum(vals) / len(vals)) for v, vals in by_variant.items() if vals
        }
        winner = max(avg_by_variant, key=lambda k: avg_by_variant[k]) if avg_by_variant else "none"
        result: Dict[str, Any] = {
            "winner": str(winner),
            "by_variant": avg_by_variant,
            "sample_count": int(sample_count),
        }
        logger.info(
            "Experiment analysis: %s, winner=%s, samples=%d",
            experiment_id,
            winner,
            sample_count,
        )
        return result
    except Exception as e:
        logger.error("Failed to analyze experiment: %s", str(e))
        return {"winner": "none", "by_variant": {}, "sample_count": 0}


def conclude_experiment(experiment_id: str, bucket: str) -> Dict[str, Any]:
    analysis = analyze_experiment(experiment_id, bucket)
    try:
        client = boto3.client("s3")
        response = client.get_object(Bucket=bucket, Key=f"experiments/{experiment_id}/config.json")
        config: Dict[str, Any] = json.loads(response["Body"].read().decode("utf-8"))
        config["status"] = "concluded"
        config["concluded_at"] = str(datetime.utcnow().isoformat())
        config["winner"] = str(analysis.get("winner", "none"))
        client.put_object(
            Bucket=bucket,
            Key=f"experiments/{experiment_id}/config.json",
            Body=json.dumps(config, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
    except Exception as e:
        logger.error("Failed to update experiment status: %s", str(e))
    conclusion: Dict[str, Any] = {
        **analysis,
        "status": "concluded",
        "experiment_id": str(experiment_id),
    }
    logger.info("Experiment concluded: %s, winner=%s", experiment_id, analysis.get("winner"))
    return conclusion


if __name__ == "__main__":
    pass
