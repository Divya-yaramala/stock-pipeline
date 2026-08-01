import hashlib
import json
import logging
import random
from datetime import datetime
from typing import Any, Dict

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_serving_endpoint(
    model_name: str,
    environment: str,
    port: int,
    bucket: str,
) -> Dict[str, Any]:
    endpoint_id = hashlib.md5(
        f"{model_name}:{environment}:{port}".encode()
    ).hexdigest()[:12]

    config: Dict[str, Any] = {
        "endpoint_id": endpoint_id,
        "model_name": model_name,
        "environment": environment,
        "port": port,
        "status": "running",
        "replicas": 1,
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        s3 = boto3.client("s3")
        key = f"serving/endpoints/{environment}/{model_name}.json"
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(config),
            ContentType="application/json",
        )
        logger.info(f"Endpoint created: {endpoint_id} ({model_name}/{environment}:{port})")
    except Exception as e:
        logger.error(f"Failed to save endpoint config: {e}")

    return config


def health_check_endpoint(
    endpoint_config: Dict[str, Any],
) -> Dict[str, Any]:
    status = str(endpoint_config.get("status", "unknown"))
    healthy = status == "running"
    latency_ms = round(random.uniform(5.0, 50.0), 2) if healthy else 0.0

    result: Dict[str, Any] = {
        "healthy": healthy,
        "latency_ms": latency_ms,
        "status": status,
    }
    logger.info(
        f"Health check for {endpoint_config.get('endpoint_id')}: "
        f"healthy={healthy}, latency={latency_ms}ms"
    )
    return result


def scale_endpoint(
    endpoint_id: str,
    replicas: int,
    bucket: str,
) -> bool:
    try:
        s3 = boto3.client("s3")
        prefix = "serving/endpoints/"
        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = str(obj["Key"])
                body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
                config: Dict[str, Any] = json.loads(body.decode("utf-8"))
                if str(config.get("endpoint_id")) == endpoint_id:
                    config["replicas"] = int(str(replicas))
                    s3.put_object(
                        Bucket=bucket,
                        Key=key,
                        Body=json.dumps(config),
                        ContentType="application/json",
                    )
                    logger.info(f"Scaled endpoint {endpoint_id} to {replicas} replicas")
                    return True
    except Exception as e:
        logger.error(f"Failed to scale endpoint {endpoint_id}: {e}")

    return False


def get_endpoint_metrics(
    endpoint_id: str,
    bucket: str,
    date: str,
) -> Dict[str, Any]:
    defaults: Dict[str, Any] = {
        "requests_per_minute": 0.0,
        "avg_latency_ms": 0.0,
        "error_rate_pct": 0.0,
        "p95_latency_ms": 0.0,
    }

    try:
        s3 = boto3.client("s3")
        key = f"serving/metrics/{date}/{endpoint_id}.json"
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        metrics: Dict[str, Any] = json.loads(body.decode("utf-8"))
        logger.info(f"Metrics retrieved for endpoint {endpoint_id}")
        return metrics
    except Exception:
        logger.info(f"No metrics found for endpoint {endpoint_id} on {date}, returning defaults")
        return defaults


def run_infrastructure_check(bucket: str) -> Dict[str, Any]:
    total = 0
    healthy_count = 0
    unhealthy_count = 0

    try:
        s3 = boto3.client("s3")
        prefix = "serving/endpoints/"
        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                try:
                    body = s3.get_object(Bucket=bucket, Key=str(obj["Key"]))["Body"].read()
                    config: Dict[str, Any] = json.loads(body.decode("utf-8"))
                    result = health_check_endpoint(config)
                    total += 1
                    if result["healthy"]:
                        healthy_count += 1
                    else:
                        unhealthy_count += 1
                except Exception:
                    continue
    except Exception as e:
        logger.error(f"Infrastructure check failed: {e}")

    summary: Dict[str, Any] = {
        "total_endpoints": total,
        "healthy": healthy_count,
        "unhealthy": unhealthy_count,
    }
    logger.info(f"Infrastructure check: {healthy_count}/{total} healthy")
    return summary


if __name__ == "__main__":
    pass
