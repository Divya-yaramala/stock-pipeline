import json
import logging
import os
from datetime import datetime

import boto3
import psutil

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

CPU_WARNING_THRESHOLD = 90.0
MEMORY_WARNING_THRESHOLD = 85.0
DISK_CRITICAL_THRESHOLD = 90.0


def get_system_resources() -> dict:
    """Return a snapshot of current CPU, memory, and disk metrics."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    resources = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": mem.percent,
        "memory_available_gb": round(mem.available / (1024**3), 2),
        "disk_usage_percent": disk.percent,
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "recorded_at": datetime.now().isoformat(),
    }

    logger.info(
        "Resource snapshot — CPU: %.1f%%, Memory: %.1f%%, Disk: %.1f%%",
        resources["cpu_percent"],
        resources["memory_percent"],
        resources["disk_usage_percent"],
    )
    return resources


def check_resource_thresholds() -> dict:
    """Check current resources against warning/critical thresholds."""
    resources = get_system_resources()

    cpu_status = "warning" if resources["cpu_percent"] > CPU_WARNING_THRESHOLD else "ok"
    memory_status = "warning" if resources["memory_percent"] > MEMORY_WARNING_THRESHOLD else "ok"
    disk_status = "critical" if resources["disk_usage_percent"] > DISK_CRITICAL_THRESHOLD else "ok"

    result = {
        "cpu": {"status": cpu_status, "value": resources["cpu_percent"]},
        "memory": {"status": memory_status, "value": resources["memory_percent"]},
        "disk": {"status": disk_status, "value": resources["disk_usage_percent"]},
    }

    for resource, data in result.items():
        if data["status"] != "ok":
            logger.warning("Resource %s is %s: %.1f%%", resource, data["status"], data["value"])

    return result


def should_run_pipeline() -> bool:
    """Return False if any resource is critical, True otherwise."""
    thresholds = check_resource_thresholds()
    for resource, data in thresholds.items():
        if data["status"] == "critical":
            logger.warning(
                "Pipeline skipped — %s is critical (%.1f%%)",
                resource,
                data["value"],
            )
            return False
    logger.info("All resources within acceptable limits — pipeline can proceed")
    return True


def record_resource_snapshot(bucket: str) -> bool:
    """Save current resource metrics to S3 at monitoring/resources/YYYY/MM/DD/HH_MM_SS.json."""
    try:
        resources = get_system_resources()
        s3 = boto3.client("s3", region_name=AWS_REGION)
        now = datetime.now()
        date_path = now.strftime("%Y/%m/%d")
        time_str = now.strftime("%H_%M_%S")
        key = f"monitoring/resources/{date_path}/{time_str}.json"
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(resources))
        logger.info("Resource snapshot saved to s3://%s/%s", bucket, key)
        return True
    except Exception as e:
        logger.error("Failed to record resource snapshot: %s", e)
        return False


if __name__ == "__main__":
    print(get_system_resources())
