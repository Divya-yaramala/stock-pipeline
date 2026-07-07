import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_STANDARD_PRICE = 0.023
S3_GLACIER_PRICE = 0.004

RETENTION_POLICIES: Dict[str, int] = {
    "raw/stocks": 90,
    "processed/anomalies": 180,
    "processed/predictions": 90,
    "processed/insights": 90,
    "processed/sentiment": 30,
    "processed/technical": 30,
    "processed/features": 30,
    "cache": 7,
    "chaos": 30,
    "testing": 30,
}


def calculate_prefix_size(bucket: str, prefix: str) -> Dict[str, Any]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    total_bytes = 0
    object_count = 0
    oldest_date: Optional[str] = None

    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                total_bytes += int(str(obj["Size"]))
                object_count += 1
                last_mod = str(obj["LastModified"])
                if oldest_date is None or last_mod < oldest_date:
                    oldest_date = last_mod
    except Exception as e:
        logger.error("Failed to calculate size for prefix %s: %s", prefix, e)

    total_size_mb = round(total_bytes / (1024**2), 4)
    result: Dict[str, Any] = {
        "prefix": prefix,
        "total_size_mb": total_size_mb,
        "object_count": object_count,
        "oldest_file_date": oldest_date,
    }
    logger.info("Prefix %s: %.2f MB, %d objects", prefix, total_size_mb, object_count)
    return result


def identify_expired_objects(
    bucket: str,
    prefix: str,
    retention_days: int,
) -> List[str]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    expired_keys: List[str] = []

    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                if obj["LastModified"] < cutoff:
                    expired_keys.append(str(obj["Key"]))
    except Exception as e:
        logger.error("Failed to identify expired objects for %s: %s", prefix, e)

    logger.info(
        "Found %d expired objects in %s (retention=%d days)",
        len(expired_keys),
        prefix,
        retention_days,
    )
    return expired_keys


def delete_expired_objects(
    bucket: str,
    keys: List[str],
    dry_run: bool = True,
) -> Dict[str, Any]:
    if dry_run:
        logger.info("DRY RUN: would delete %d objects from %s", len(keys), bucket)
        return {"deleted": 0, "failed": 0, "dry_run": True, "would_delete": len(keys)}

    s3 = boto3.client("s3", region_name=AWS_REGION)
    deleted = 0
    failed = 0
    batch_size = 1000

    for i in range(0, len(keys), batch_size):
        batch = keys[i : i + batch_size]
        objects = [{"Key": k} for k in batch]
        try:
            response = s3.delete_objects(Bucket=bucket, Delete={"Objects": objects})
            deleted += len(response.get("Deleted", []))
            failed += len(response.get("Errors", []))
        except Exception as e:
            logger.error("Batch deletion failed: %s", e)
            failed += len(batch)

    logger.info("Deleted %d objects, %d failed (dry_run=%s)", deleted, failed, dry_run)
    return {"deleted": deleted, "failed": failed, "dry_run": False}


def move_to_glacier(bucket: str, keys: List[str]) -> Dict[str, Any]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    moved = 0
    failed = 0

    for key in keys:
        try:
            s3.copy_object(
                Bucket=bucket,
                CopySource={"Bucket": bucket, "Key": key},
                Key=key,
                StorageClass="GLACIER",
                MetadataDirective="COPY",
            )
            moved += 1
        except Exception as e:
            logger.error("Failed to move %s to Glacier: %s", key, e)
            failed += 1

    logger.info("Moved %d objects to Glacier, %d failed", moved, failed)
    return {"moved": moved, "failed": failed}


def calculate_cost_savings(size_gb: float, action: str) -> Dict[str, float]:
    size = float(str(size_gb))
    if action == "delete":
        monthly = round(size * S3_STANDARD_PRICE, 4)
    else:
        monthly = round(size * (S3_STANDARD_PRICE - S3_GLACIER_PRICE), 4)

    annual = round(monthly * 12, 4)
    logger.info(
        "Estimated savings for %s (%.2f GB): $%.4f/month, $%.4f/year",
        action,
        size,
        monthly,
        annual,
    )
    return {"monthly_savings": monthly, "annual_savings": annual}


def run_s3_optimization(
    bucket: str,
    dry_run: bool = True,
) -> Dict[str, Any]:
    date = datetime.utcnow().strftime("%Y/%m/%d")
    total_expired = 0
    total_deleted = 0
    total_size_mb = 0.0
    prefix_reports: List[Dict[str, Any]] = []

    for prefix, retention_days in RETENTION_POLICIES.items():
        size_info = calculate_prefix_size(bucket, prefix)
        total_size_mb += float(str(size_info["total_size_mb"]))
        expired_keys = identify_expired_objects(bucket, prefix, retention_days)
        total_expired += len(expired_keys)

        result = delete_expired_objects(bucket, expired_keys, dry_run=dry_run)
        total_deleted += int(str(result.get("deleted", 0)))

        prefix_reports.append(
            {
                "prefix": prefix,
                "retention_days": retention_days,
                "expired_keys": len(expired_keys),
                "deleted": result.get("deleted", 0),
                "dry_run": dry_run,
            }
        )

    size_gb = total_size_mb / 1024
    savings = calculate_cost_savings(size_gb, "delete")

    report: Dict[str, Any] = {
        "date": date,
        "dry_run": dry_run,
        "total_expired": total_expired,
        "total_deleted": total_deleted,
        "total_size_mb": round(total_size_mb, 2),
        "estimated_savings": savings,
        "prefixes": prefix_reports,
        "generated_at": datetime.utcnow().isoformat(),
    }

    s3 = boto3.client("s3", region_name=AWS_REGION)
    report_key = f"reports/s3_optimization/{date}/report.json"
    try:
        s3.put_object(
            Bucket=bucket,
            Key=report_key,
            Body=json.dumps(report),
            ContentType="application/json",
        )
        logger.info("S3 optimization report saved to s3://%s/%s", bucket, report_key)
    except Exception as e:
        logger.error("Failed to save optimization report: %s", e)

    logger.info(
        "S3 Optimization Complete: %d objects processed, %d deleted",
        total_expired,
        total_deleted,
    )
    return report


if __name__ == "__main__":
    pass
