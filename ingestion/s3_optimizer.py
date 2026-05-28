import logging
import os
from datetime import datetime, timedelta, timezone

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_PRICE_PER_GB = 0.023


def get_s3_storage_summary(bucket: str) -> dict:
    """List all objects in bucket, calculate total size, and group by prefix."""
    s3 = boto3.client("s3", region_name=AWS_REGION)
    prefixes = ["raw/", "processed/", "errors/", "lineage/", "monitoring/", "reports/"]
    breakdown: dict = {p: 0.0 for p in prefixes}
    total_bytes = 0

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            size = obj["Size"]
            total_bytes += size
            matched = False
            for prefix in prefixes:
                if obj["Key"].startswith(prefix):
                    breakdown[prefix] += size
                    matched = True
                    break
            if not matched:
                breakdown.setdefault("other/", 0.0)
                breakdown["other/"] += size

    total_mb = total_bytes / (1024**2)
    total_gb = total_bytes / (1024**3)

    summary = {
        "total_bytes": total_bytes,
        "total_mb": round(total_mb, 4),
        "total_gb": round(total_gb, 4),
        "breakdown_mb": {k: round(v / (1024**2), 4) for k, v in breakdown.items()},
    }

    logger.info(
        "S3 storage summary for %s: %.2f MB total (%.4f GB)",
        bucket,
        total_mb,
        total_gb,
    )
    for prefix, size_bytes in breakdown.items():
        if size_bytes > 0:
            logger.info("  %s: %.2f MB", prefix, size_bytes / (1024**2))

    return summary


def archive_old_raw_data(bucket: str, days_to_keep: int = 30) -> int:
    """Move raw/stocks/ files older than days_to_keep to archive/raw/stocks/."""
    s3 = boto3.client("s3", region_name=AWS_REGION)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    archived = 0

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix="raw/stocks/"):
        for obj in page.get("Contents", []):
            last_modified = obj["LastModified"]
            if last_modified < cutoff:
                src_key = obj["Key"]
                dst_key = "archive/" + src_key
                try:
                    s3.copy_object(
                        Bucket=bucket,
                        CopySource={"Bucket": bucket, "Key": src_key},
                        Key=dst_key,
                    )
                    s3.delete_object(Bucket=bucket, Key=src_key)
                    archived += 1
                    logger.info("Archived %s → %s", src_key, dst_key)
                except Exception as e:
                    logger.error("Failed to archive %s: %s", src_key, e)

    logger.info("Archived %d raw data file(s) older than %d days", archived, days_to_keep)
    return archived


def delete_old_monitoring_data(bucket: str, days_to_keep: int = 7) -> int:
    """Delete monitoring/ files older than days_to_keep days."""
    s3 = boto3.client("s3", region_name=AWS_REGION)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    deleted = 0

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix="monitoring/"):
        for obj in page.get("Contents", []):
            last_modified = obj["LastModified"]
            if last_modified < cutoff:
                try:
                    s3.delete_object(Bucket=bucket, Key=obj["Key"])
                    deleted += 1
                except Exception as e:
                    logger.error("Failed to delete %s: %s", obj["Key"], e)

    logger.info("Deleted %d monitoring file(s) older than %d days", deleted, days_to_keep)
    return deleted


def generate_cost_report(bucket: str) -> dict:
    """Estimate monthly S3 costs based on current storage usage."""
    summary = get_s3_storage_summary(bucket)
    storage_gb = summary["total_gb"]
    estimated_cost = round(storage_gb * S3_PRICE_PER_GB, 4)

    report = {
        "bucket": bucket,
        "generated_at": datetime.now().isoformat(),
        "storage_gb": storage_gb,
        "estimated_monthly_cost_usd": estimated_cost,
        "breakdown_by_prefix": summary["breakdown_mb"],
    }

    logger.info(
        "Cost estimate for %s: %.4f GB → $%.4f/month",
        bucket,
        storage_gb,
        estimated_cost,
    )
    return report


def run_s3_optimization() -> None:
    """Archive old raw data, purge old monitoring files, and report cost estimate."""
    bucket = os.environ.get("AWS_BUCKET_NAME", "")

    archived = archive_old_raw_data(bucket)
    deleted = delete_old_monitoring_data(bucket)
    report = generate_cost_report(bucket)

    logger.info(
        "S3 optimization complete — archived: %d, deleted: %d, estimated cost: $%.4f/month",
        archived,
        deleted,
        report["estimated_monthly_cost_usd"],
    )


if __name__ == "__main__":
    run_s3_optimization()
