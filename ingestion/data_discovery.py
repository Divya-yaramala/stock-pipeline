import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def discover_s3_datasets(bucket: str) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3")
    datasets: List[Dict[str, Any]] = []
    prefixes: List[str] = []

    try:
        response = s3.list_objects_v2(Bucket=bucket, Delimiter="/")
        for cp in response.get("CommonPrefixes", []):
            prefixes.append(str(cp["Prefix"]))
    except Exception as e:
        logger.error("Failed to list bucket prefixes: %s", e)
        return datasets

    for prefix in prefixes:
        object_count = 0
        total_bytes = 0
        last_modified = ""
        paginator = s3.get_paginator("list_objects_v2")
        try:
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    object_count += 1
                    total_bytes += int(str(obj.get("Size", 0)))
                    lm = str(obj.get("LastModified", ""))
                    if lm > last_modified:
                        last_modified = lm
        except Exception:
            pass
        datasets.append(
            {
                "prefix": prefix,
                "object_count": object_count,
                "size_mb": round(total_bytes / (1024 * 1024), 3),
                "last_modified": last_modified,
            }
        )

    logger.info("Discovered %d datasets in bucket %s", len(datasets), bucket)
    return datasets


def profile_dataset(
    bucket: str,
    prefix: str,
    sample_size: int = 5,
) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    schema: Dict[str, str] = {}
    null_counts: Dict[str, int] = {}
    records_sampled = 0

    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=sample_size)
        for obj in response.get("Contents", []):
            key = str(obj["Key"])
            try:
                data_obj = s3.get_object(Bucket=bucket, Key=key)
                content = data_obj["Body"].read().decode("utf-8")
                record = json.loads(content)
                if isinstance(record, dict):
                    for field, value in record.items():
                        field_str = str(field)
                        schema[field_str] = type(value).__name__
                        if value is None:
                            null_counts[field_str] = null_counts.get(field_str, 0) + 1
                    records_sampled += 1
            except Exception:
                pass
    except Exception as e:
        logger.error("Failed to profile dataset %s: %s", prefix, e)

    profile: Dict[str, Any] = {
        "prefix": prefix,
        "schema": schema,
        "null_counts": null_counts,
        "records_sampled": records_sampled,
    }
    logger.info("Profiling complete for %s: %d fields, %d records sampled",
                prefix, len(schema), records_sampled)
    return profile


def search_datasets(bucket: str, query: str) -> List[Dict[str, Any]]:
    all_datasets = discover_s3_datasets(bucket)
    matches = [d for d in all_datasets if query.lower() in str(d["prefix"]).lower()]
    logger.info("Search '%s' returned %d/%d datasets", query, len(matches), len(all_datasets))
    return matches


def get_dataset_stats(bucket: str, prefix: str) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    record_count = 0
    total_bytes = 0
    dates: List[str] = []
    paginator = s3.get_paginator("list_objects_v2")

    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                record_count += 1
                total_bytes += int(str(obj.get("Size", 0)))
                lm = str(obj.get("LastModified", ""))
                if lm:
                    dates.append(lm)
    except Exception as e:
        logger.error("Failed to get stats for %s: %s", prefix, e)

    size_mb = round(total_bytes / (1024 * 1024), 3)
    avg_kb = round((total_bytes / record_count / 1024), 3) if record_count > 0 else 0.0
    date_min = min(dates) if dates else ""
    date_max = max(dates) if dates else ""

    stats: Dict[str, Any] = {
        "record_count": record_count,
        "date_range": {"min": date_min, "max": date_max},
        "size_mb": size_mb,
        "avg_record_size_kb": avg_kb,
    }
    logger.info("Dataset stats for %s: %d records, %.3f MB", prefix, record_count, size_mb)
    return stats


def run_data_discovery(bucket: str) -> Dict[str, Any]:
    datasets = discover_s3_datasets(bucket)
    sorted_datasets = sorted(datasets, key=lambda d: float(str(d["size_mb"])), reverse=True)
    top5 = sorted_datasets[:5]

    profiles: List[Dict[str, Any]] = []
    for ds in top5:
        profile = profile_dataset(bucket, str(ds["prefix"]))
        profiles.append(profile)

    report: Dict[str, Any] = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "datasets": datasets,
        "profiles": profiles,
        "total_datasets": len(datasets),
    }

    now = datetime.utcnow()
    key = f"reports/discovery/{now.year}/{now.month:02d}/{now.day:02d}/report.json"
    try:
        s3 = boto3.client("s3")
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(report))
    except Exception as e:
        logger.error("Failed to save discovery report: %s", e)

    logger.info("Data Discovery Complete: %d datasets found", len(datasets))
    return report


if __name__ == "__main__":
    pass
