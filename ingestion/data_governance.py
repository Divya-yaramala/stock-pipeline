import hashlib
import json
import logging
from datetime import datetime, timezone

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PII_FIELDS = {"email", "phone", "ssn", "dob"}
BUSINESS_FIELDS = {"ticker", "price", "close", "volume", "trade_date"}


def classify_data(dataset_name: str, data_sample: dict) -> dict:
    keys = {k.lower() for k in data_sample.keys()}
    pii_found = keys & PII_FIELDS

    if pii_found:
        result = {
            "classification": "CONFIDENTIAL",
            "reason": f"PII fields detected: {sorted(pii_found)}",
            "pii_detected": True,
        }
    elif keys & BUSINESS_FIELDS:
        result = {
            "classification": "INTERNAL",
            "reason": "Business data — internal use only",
            "pii_detected": False,
        }
    else:
        result = {
            "classification": "PUBLIC",
            "reason": "No PII detected — freely shareable",
            "pii_detected": False,
        }

    logger.info(
        "classify_data: dataset=%s classification=%s pii=%s",
        dataset_name,
        result["classification"],
        result["pii_detected"],
    )
    return result


def apply_data_masking(data: dict, fields_to_mask: list) -> dict:
    masked = dict(data)
    for field in fields_to_mask:
        if field in masked:
            raw = str(masked[field]).encode("utf-8")
            masked[field] = hashlib.sha256(raw).hexdigest()
    logger.info("apply_data_masking: masked fields=%s", fields_to_mask)
    return masked


def create_audit_log(
    action: str,
    dataset: str,
    user: str,
    details: dict,
    bucket: str,
) -> bool:
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    date_path = now.strftime("%Y/%m/%d")
    key = f"governance/audit/{date_path}/{now.strftime('%H%M%S%f')}.json"

    entry = {
        "action": action,
        "dataset": dataset,
        "user": user,
        "details": details,
        "timestamp": timestamp,
    }

    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(entry, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Audit entry created: action=%s dataset=%s user=%s", action, dataset, user)
        return True
    except Exception as e:
        logger.error("Failed to create audit log: %s", e)
        return False


def check_retention_policy(dataset: str, created_date: str, retention_days: int) -> dict:
    created = datetime.strptime(created_date, "%Y-%m-%d")
    days_old = (datetime.now() - created).days
    should_delete = days_old > retention_days

    result = {
        "should_delete": should_delete,
        "days_old": days_old,
        "retention_days": retention_days,
    }
    logger.info(
        "check_retention_policy: dataset=%s days_old=%d retention=%d should_delete=%s",
        dataset,
        days_old,
        retention_days,
        should_delete,
    )
    return result


def generate_compliance_report(bucket: str) -> dict:
    from ingestion.data_catalog import DATASETS

    total = len(DATASETS)
    classified = 0
    compliant = 0
    violations = []

    s3 = boto3.client("s3")
    for ds in DATASETS:
        name = ds["name"]
        key = f"governance/classification/{name}.json"
        try:
            s3.get_object(Bucket=bucket, Key=key)
            classified += 1
            compliant += 1
        except Exception:
            violations.append(f"{name}: missing classification record")

    score = (compliant / total * 100) if total > 0 else 0.0
    logger.info("Compliance score: %d/%d datasets compliant (%.1f%%)", compliant, total, score)
    return {
        "total_datasets": total,
        "classified": classified,
        "compliant": compliant,
        "violations": violations,
    }


def run_governance_check(bucket: str) -> dict:
    report = generate_compliance_report(bucket)
    logger.info("Governance check complete")
    return report


if __name__ == "__main__":
    pass
