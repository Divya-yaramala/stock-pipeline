"""Data archival pipeline — Glacier archival and expired data deletion."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3

logger = logging.getLogger(__name__)

ARCHIVE_POLICIES: List[Dict[str, Any]] = [
    {"prefix": "raw/stocks", "archive_after_days": 90, "delete_after_days": 365},
    {"prefix": "processed/anomalies", "archive_after_days": 180, "delete_after_days": 730},
    {"prefix": "processed/predictions", "archive_after_days": 90, "delete_after_days": 365},
    {"prefix": "processed/insights", "archive_after_days": 90, "delete_after_days": 365},
    {"prefix": "processed/sentiment", "archive_after_days": 30, "delete_after_days": 180},
    {"prefix": "models/experiments", "archive_after_days": 90, "delete_after_days": 730},
]


def identify_archive_candidates(
    bucket: str, prefix: str, archive_after_days: int
) -> List[Dict[str, Any]]:
    """Return objects older than archive_after_days that are still in Standard storage."""
    s3 = boto3.client("s3")
    cutoff = datetime.utcnow() - timedelta(days=archive_after_days)
    candidates: List[Dict[str, Any]] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            last_modified: datetime = obj["LastModified"].replace(tzinfo=None)
            storage_class: str = obj.get("StorageClass", "STANDARD")
            if last_modified < cutoff and storage_class == "STANDARD":
                candidates.append(
                    {
                        "key": obj["Key"],
                        "last_modified": last_modified.isoformat(),
                        "size_bytes": obj["Size"],
                        "storage_class": storage_class,
                    }
                )
    return candidates


def identify_deletion_candidates(
    bucket: str, prefix: str, delete_after_days: int
) -> List[Dict[str, Any]]:
    """Return objects older than delete_after_days regardless of storage class."""
    s3 = boto3.client("s3")
    cutoff = datetime.utcnow() - timedelta(days=delete_after_days)
    candidates: List[Dict[str, Any]] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            last_modified: datetime = obj["LastModified"].replace(tzinfo=None)
            if last_modified < cutoff:
                candidates.append(
                    {
                        "key": obj["Key"],
                        "last_modified": last_modified.isoformat(),
                        "size_bytes": obj["Size"],
                        "storage_class": obj.get("StorageClass", "STANDARD"),
                    }
                )
    return candidates


def archive_to_glacier(
    bucket: str, objects: List[Dict[str, Any]], dry_run: bool = True
) -> Dict[str, Any]:
    """Copy objects to Glacier storage class. Skips actual copy when dry_run=True."""
    s3 = boto3.client("s3")
    archived: List[str] = []
    errors: List[str] = []

    for obj in objects:
        key: str = str(obj["key"])
        if dry_run:
            archived.append(key)
            continue
        try:
            s3.copy_object(
                Bucket=bucket,
                CopySource={"Bucket": bucket, "Key": key},
                Key=key,
                StorageClass="GLACIER",
                MetadataDirective="COPY",
            )
            archived.append(key)
        except Exception as exc:
            errors.append(f"{key}: {exc}")

    return {
        "archived_count": len(archived),
        "archived_keys": archived,
        "errors": errors,
        "dry_run": dry_run,
    }


def delete_expired_data(
    bucket: str, objects: List[Dict[str, Any]], dry_run: bool = True
) -> Dict[str, Any]:
    """Delete objects that have passed their retention period. Skips when dry_run=True."""
    s3 = boto3.client("s3")
    deleted: List[str] = []
    errors: List[str] = []

    for i in range(0, len(objects), 1000):
        batch = objects[i : i + 1000]
        keys = [{"Key": str(o["key"])} for o in batch]
        if dry_run:
            deleted.extend(str(o["key"]) for o in batch)
            continue
        try:
            response = s3.delete_objects(
                Bucket=bucket, Delete={"Objects": keys, "Quiet": True}
            )
            deleted.extend(k["Key"] for k in keys)
            for err in response.get("Errors", []):
                errors.append(f"{err['Key']}: {err['Message']}")
        except Exception as exc:
            errors.append(str(exc))

    return {
        "deleted_count": len(deleted),
        "deleted_keys": deleted,
        "errors": errors,
        "dry_run": dry_run,
    }


def generate_archival_report(
    bucket: str,
    archive_results: List[Dict[str, Any]],
    delete_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Save an archival summary to S3 and return the report dict."""
    s3 = boto3.client("s3")
    today = datetime.utcnow().strftime("%Y/%m/%d")
    total_archived = sum(int(r.get("archived_count", 0)) for r in archive_results)
    total_deleted = sum(int(r.get("deleted_count", 0)) for r in delete_results)

    report: Dict[str, Any] = {
        "report_date": today,
        "total_archived": total_archived,
        "total_deleted": total_deleted,
        "archive_results": archive_results,
        "delete_results": delete_results,
        "generated_at": datetime.utcnow().isoformat(),
    }

    key = f"reports/archival/{today}/report.json"
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(report, indent=2),
        ContentType="application/json",
    )
    logger.info("Archival report saved to s3://%s/%s", bucket, key)
    return report


def run_archival_pipeline(bucket: str, dry_run: bool = True) -> Dict[str, Any]:
    """Run the full archival pipeline across all ARCHIVE_POLICIES."""
    archive_results: List[Dict[str, Any]] = []
    delete_results: List[Dict[str, Any]] = []

    for policy in ARCHIVE_POLICIES:
        prefix: str = str(policy["prefix"])
        archive_after: int = int(policy["archive_after_days"])
        delete_after: int = int(policy["delete_after_days"])

        archive_candidates = identify_archive_candidates(bucket, prefix, archive_after)
        result = archive_to_glacier(bucket, archive_candidates, dry_run=dry_run)
        result["prefix"] = prefix
        archive_results.append(result)

        delete_candidates = identify_deletion_candidates(bucket, prefix, delete_after)
        del_result = delete_expired_data(bucket, delete_candidates, dry_run=dry_run)
        del_result["prefix"] = prefix
        delete_results.append(del_result)

    return generate_archival_report(bucket, archive_results, delete_results)
