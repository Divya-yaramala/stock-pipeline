import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import boto3

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _load_catalog_entry(dataset_name: str, bucket: str, s3: Any) -> Dict:
    key = f"catalog/datasets/{dataset_name}/metadata.json"
    response = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(response["Body"].read().decode("utf-8"))


def _save_catalog_entry(dataset_name: str, entry: Dict, bucket: str, s3: Any) -> None:
    key = f"catalog/datasets/{dataset_name}/metadata.json"
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(entry, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def tag_dataset(dataset_name: str, tags: List[str], bucket: str) -> bool:
    s3 = boto3.client("s3")
    try:
        entry = _load_catalog_entry(dataset_name, bucket, s3)
        existing = entry.get("tags", [])
        entry["tags"] = list(set(existing + tags))
        entry["tagged_at"] = datetime.now(timezone.utc).isoformat()
        _save_catalog_entry(dataset_name, entry, bucket, s3)
        logger.info("Tagged %s with: %s", dataset_name, tags)
        return True
    except Exception as e:
        logger.error("Failed to tag %s: %s", dataset_name, e)
        return False


def set_data_owner(dataset_name: str, owner: str, team: str, bucket: str) -> bool:
    s3 = boto3.client("s3")
    try:
        entry = _load_catalog_entry(dataset_name, bucket, s3)
        entry["owner"] = owner
        entry["team"] = team
        entry["ownership_updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_catalog_entry(dataset_name, entry, bucket, s3)
        logger.info("Ownership updated for %s: owner=%s team=%s", dataset_name, owner, team)
        return True
    except Exception as e:
        logger.error("Failed to set owner for %s: %s", dataset_name, e)
        return False


def add_data_contract(dataset_name: str, contract: Dict, bucket: str) -> bool:
    s3 = boto3.client("s3")
    try:
        entry = _load_catalog_entry(dataset_name, bucket, s3)
        entry["contract"] = {
            **contract,
            "added_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_catalog_entry(dataset_name, entry, bucket, s3)
        logger.info("Data contract added for %s: %s", dataset_name, contract)
        return True
    except Exception as e:
        logger.error("Failed to add contract for %s: %s", dataset_name, e)
        return False


def check_data_contracts(bucket: str) -> List[Dict]:
    s3 = boto3.client("s3")
    violations = []

    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix="catalog/datasets/")
        for obj in response.get("Contents", []):
            if not obj["Key"].endswith("metadata.json"):
                continue
            try:
                data = s3.get_object(Bucket=bucket, Key=obj["Key"])
                entry = json.loads(data["Body"].read().decode("utf-8"))
                contract = entry.get("contract")
                if not contract:
                    continue

                dataset_name = entry.get("dataset_name", "unknown")
                last_updated = entry.get("last_updated", "")
                freshness_sla = contract.get("freshness_sla_hours", 25)
                quality_threshold = contract.get("quality_threshold_pct", 95.0)

                if last_updated:
                    try:
                        last_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                        if last_dt.tzinfo is None:
                            from datetime import timezone as tz

                            last_dt = last_dt.replace(tzinfo=tz.utc)
                        hours_since = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                        if hours_since > freshness_sla:
                            violations.append(
                                {
                                    "dataset": dataset_name,
                                    "violation": "freshness_sla_breach",
                                    "hours_since_update": round(hours_since, 1),
                                    "sla_hours": freshness_sla,
                                }
                            )
                    except Exception:
                        pass

                actual_quality = entry.get("quality_score", 100.0)
                if actual_quality < quality_threshold:
                    violations.append(
                        {
                            "dataset": dataset_name,
                            "violation": "quality_below_threshold",
                            "actual": actual_quality,
                            "threshold": quality_threshold,
                        }
                    )
            except Exception:
                pass
    except Exception as e:
        logger.error("Contract check failed: %s", e)

    logger.info("Contract check complete: %d violation(s) found", len(violations))
    return violations


def generate_catalog_report(bucket: str) -> Dict:
    s3 = boto3.client("s3")
    datasets = []
    contracts_count = 0

    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix="catalog/datasets/")
        for obj in response.get("Contents", []):
            if not obj["Key"].endswith("metadata.json"):
                continue
            try:
                data = s3.get_object(Bucket=bucket, Key=obj["Key"])
                entry = json.loads(data["Body"].read().decode("utf-8"))
                datasets.append(entry)
                if entry.get("contract"):
                    contracts_count += 1
            except Exception:
                pass
    except Exception as e:
        logger.error("Failed to generate catalog report: %s", e)

    violations = check_data_contracts(bucket)

    logger.info(
        "Catalog report: %d datasets, %d with contracts, %d violations",
        len(datasets),
        contracts_count,
        len(violations),
    )
    return {
        "datasets": datasets,
        "total_datasets": len(datasets),
        "datasets_with_contracts": contracts_count,
        "violations": violations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    print(generate_catalog_report(os.getenv("AWS_BUCKET_NAME", "")))
