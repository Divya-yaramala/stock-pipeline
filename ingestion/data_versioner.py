import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def generate_version_id(ticker: str, date: str, data: Dict[str, Any]) -> str:
    raw = f"{ticker}{date}{json.dumps(data, sort_keys=True)}"
    version_id = hashlib.md5(raw.encode()).hexdigest()[:8]
    logger.info("Generated version ID %s for %s on %s", version_id, ticker, date)
    return version_id


def save_versioned_data(
    data: Dict[str, Any],
    ticker: str,
    pipeline_step: str,
    bucket: str,
    date: str,
) -> str:
    version_id = generate_version_id(ticker, date, data)
    date_parts = date.replace("-", "/")
    key = f"versions/{date_parts}/{pipeline_step}/{ticker}_{version_id}.json"

    payload: Dict[str, Any] = {
        "data": data,
        "version_id": version_id,
        "ticker": ticker,
        "pipeline_step": pipeline_step,
        "created_at": datetime.utcnow().isoformat(),
    }

    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload),
        ContentType="application/json",
    )
    logger.info("Saved versioned data %s to s3://%s/%s", version_id, bucket, key)
    return version_id


def list_versions(
    ticker: str,
    pipeline_step: str,
    bucket: str,
    date: str,
) -> List[Dict[str, Any]]:
    date_parts = date.replace("-", "/")
    prefix = f"versions/{date_parts}/{pipeline_step}/{ticker}_"

    s3 = boto3.client("s3", region_name=AWS_REGION)
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    objects = response.get("Contents", [])

    versions: List[Dict[str, Any]] = []
    for obj in objects:
        key = str(obj["Key"])
        filename = key.split("/")[-1]
        version_id = filename.replace(f"{ticker}_", "").replace(".json", "")
        last_modified = obj.get("LastModified", "")
        versions.append(
            {
                "version_id": version_id,
                "created_at": (
                    last_modified.isoformat()
                    if hasattr(last_modified, "isoformat")
                    else str(last_modified)
                ),
            }
        )

    logger.info("Found %d versions for %s/%s on %s", len(versions), ticker, pipeline_step, date)
    return versions


def rollback_to_version(
    ticker: str,
    pipeline_step: str,
    version_id: str,
    bucket: str,
    date: str,
) -> Dict[str, Any]:
    date_parts = date.replace("-", "/")
    key = f"versions/{date_parts}/{pipeline_step}/{ticker}_{version_id}.json"

    s3 = boto3.client("s3", region_name=AWS_REGION)
    response = s3.get_object(Bucket=bucket, Key=key)
    payload: Dict[str, Any] = json.loads(response["Body"].read().decode("utf-8"))

    logger.info("Rolled back %s/%s to version %s", ticker, pipeline_step, version_id)
    return payload


def compare_versions(
    ticker: str,
    pipeline_step: str,
    version_id_1: str,
    version_id_2: str,
    bucket: str,
    date: str,
) -> Dict[str, Any]:
    v1 = rollback_to_version(ticker, pipeline_step, version_id_1, bucket, date)
    v2 = rollback_to_version(ticker, pipeline_step, version_id_2, bucket, date)

    data1: Dict[str, Any] = v1.get("data", {})
    data2: Dict[str, Any] = v2.get("data", {})

    keys1 = set(data1.keys())
    keys2 = set(data2.keys())

    added_keys = list(keys2 - keys1)
    removed_keys = list(keys1 - keys2)
    changed_keys = [k for k in keys1 & keys2 if data1[k] != data2[k]]

    result: Dict[str, Any] = {
        "added_keys": added_keys,
        "removed_keys": removed_keys,
        "changed_keys": changed_keys,
    }
    logger.info(
        "Version comparison: %d added, %d removed, %d changed",
        len(added_keys),
        len(removed_keys),
        len(changed_keys),
    )
    return result


if __name__ == "__main__":
    pass
