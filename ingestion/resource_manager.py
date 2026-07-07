import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import boto3
import psutil

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_PRICE_PER_GB = 0.023

CPU_THRESHOLD = 80.0
MEMORY_THRESHOLD = 85.0
DISK_THRESHOLD = 90.0


def get_system_metrics() -> Dict[str, float]:
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    metrics: Dict[str, float] = {
        "cpu_pct": float(psutil.cpu_percent(interval=0.1)),
        "memory_pct": float(mem.percent),
        "disk_pct": float(disk.percent),
    }
    logger.info(
        "System metrics — CPU: %.1f%%, Memory: %.1f%%, Disk: %.1f%%",
        metrics["cpu_pct"],
        metrics["memory_pct"],
        metrics["disk_pct"],
    )
    return metrics


def check_resource_health(metrics: Dict[str, float]) -> Dict[str, Any]:
    warnings: List[str] = []
    critical: List[str] = []

    cpu = float(str(metrics.get("cpu_pct", 0.0)))
    memory = float(str(metrics.get("memory_pct", 0.0)))
    disk = float(str(metrics.get("disk_pct", 0.0)))

    if cpu > CPU_THRESHOLD:
        warnings.append(f"CPU at {cpu:.1f}% (threshold {CPU_THRESHOLD}%)")
    if memory > MEMORY_THRESHOLD:
        critical.append(f"Memory at {memory:.1f}% (threshold {MEMORY_THRESHOLD}%)")
    if disk > DISK_THRESHOLD:
        critical.append(f"Disk at {disk:.1f}% (threshold {DISK_THRESHOLD}%)")

    healthy = len(warnings) == 0 and len(critical) == 0
    result: Dict[str, Any] = {
        "healthy": healthy,
        "warnings": warnings,
        "critical": critical,
    }
    logger.info(
        "Resource health: healthy=%s, warnings=%d, critical=%d",
        healthy,
        len(warnings),
        len(critical),
    )
    return result


def estimate_pipeline_resources(
    num_tickers: int = 5,
    days_of_data: int = 90,
) -> Dict[str, Any]:
    bytes_per_record = 1024
    total_records = num_tickers * days_of_data
    storage_bytes = total_records * bytes_per_record
    memory_needed_mb = round(storage_bytes * 3 / (1024**2), 2)
    storage_needed_gb = round(storage_bytes / (1024**3), 4)
    api_calls_needed = num_tickers * 4

    estimate: Dict[str, Any] = {
        "num_tickers": num_tickers,
        "days_of_data": days_of_data,
        "memory_needed_mb": memory_needed_mb,
        "storage_needed_gb": storage_needed_gb,
        "api_calls_needed": api_calls_needed,
    }
    logger.info(
        "Pipeline resource estimate: %.2f MB RAM, %.4f GB storage, %d API calls",
        memory_needed_mb,
        storage_needed_gb,
        api_calls_needed,
    )
    return estimate


def check_s3_quota(bucket: str) -> Dict[str, Any]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    total_objects = 0
    total_bytes = 0

    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                total_objects += 1
                total_bytes += int(str(obj["Size"]))
    except Exception as e:
        logger.error("Failed to list S3 objects: %s", e)

    total_gb = round(total_bytes / (1024**3), 4)
    monthly_cost = round(total_gb * S3_PRICE_PER_GB, 4)

    result: Dict[str, Any] = {
        "total_objects": total_objects,
        "total_size_gb": total_gb,
        "estimated_monthly_cost": monthly_cost,
    }
    logger.info("S3 quota: %d objects, %.4f GB, $%.4f/month", total_objects, total_gb, monthly_cost)
    return result


def run_resource_check(bucket: str) -> Dict[str, Any]:
    date = datetime.utcnow().strftime("%Y/%m/%d")
    metrics = get_system_metrics()
    health = check_resource_health(metrics)
    s3_quota = check_s3_quota(bucket)

    report: Dict[str, Any] = {
        "date": date,
        "metrics": metrics,
        "healthy": health["healthy"],
        "warnings": health["warnings"],
        "critical": health["critical"],
        "s3_quota": s3_quota,
        "generated_at": datetime.utcnow().isoformat(),
    }

    s3 = boto3.client("s3", region_name=AWS_REGION)
    key = f"monitoring/resources/{date}/check.json"
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(report),
            ContentType="application/json",
        )
        logger.info("Resource check saved to s3://%s/%s", bucket, key)
    except Exception as e:
        logger.error("Failed to save resource check: %s", e)

    logger.info(
        "Resource check complete: healthy=%s, warnings=%d, critical=%d",
        health["healthy"],
        len(health["warnings"]),
        len(health["critical"]),
    )
    return report


if __name__ == "__main__":
    pass
