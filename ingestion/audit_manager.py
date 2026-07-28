import datetime
import hashlib
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AUDIT_CATEGORIES: List[str] = [
    "data_access",
    "data_modification",
    "pipeline_execution",
    "model_training",
    "secret_access",
    "compliance_check",
    "schema_change",
    "config_change",
]


def create_audit_entry(
    category: str,
    action: str,
    actor: str,
    resource: str,
    details: Optional[Dict[str, Any]] = None,
    outcome: str = "success",
) -> Dict[str, Any]:
    if category not in AUDIT_CATEGORIES:
        raise ValueError(
            f"Invalid audit category: '{category}'. Must be one of {AUDIT_CATEGORIES}"
        )

    audit_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow()

    entry: Dict[str, Any] = {
        "audit_id": audit_id,
        "category": category,
        "action": action,
        "actor": actor,
        "resource": resource,
        "outcome": outcome,
        "timestamp": now.isoformat(),
    }
    if details:
        entry["details"] = details

    logger.info(f"Audit entry created: {audit_id} | {category} | {action} | {outcome}")
    return entry


def save_audit_entry(
    entry: Dict[str, Any],
    bucket: str,
) -> bool:
    s3 = boto3.client("s3")
    try:
        now = datetime.datetime.utcnow()
        date_path = now.strftime("%Y/%m/%d")
        category = str(entry.get("category", "unknown"))
        audit_id = str(entry.get("audit_id", str(uuid.uuid4())))
        key = f"audit/entries/{date_path}/{category}/{audit_id}.json"
        safe_entry = {k: v for k, v in entry.items() if k != "details"}
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(safe_entry))
        return True
    except Exception as e:
        logger.error(f"Failed to save audit entry: {e}")
        return False


def search_audit_logs(
    bucket: str,
    date: str,
    category: Optional[str] = None,
    actor: Optional[str] = None,
    outcome: Optional[str] = None,
) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3")
    prefix = f"audit/entries/{date}/"
    if category:
        prefix = f"audit/entries/{date}/{category}/"

    entries: List[Dict[str, Any]] = []
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        for obj in response.get("Contents", []):
            key = str(obj["Key"])
            resp = s3.get_object(Bucket=bucket, Key=key)
            entry = json.loads(resp["Body"].read())
            if actor and str(entry.get("actor", "")) != actor:
                continue
            if outcome and str(entry.get("outcome", "")) != outcome:
                continue
            entries.append(entry)
    except Exception as e:
        logger.error(f"Failed to search audit logs: {e}")

    logger.info(f"Audit search returned {len(entries)} entries")
    return entries


def generate_audit_summary(
    bucket: str,
    date: str,
) -> Dict[str, Any]:
    all_entries = search_audit_logs(bucket, date)
    by_category: Dict[str, int] = {}
    by_outcome: Dict[str, int] = {}

    for entry in all_entries:
        cat = str(entry.get("category", "unknown"))
        out = str(entry.get("outcome", "unknown"))
        by_category[cat] = by_category.get(cat, 0) + 1
        by_outcome[out] = by_outcome.get(out, 0) + 1

    suspicious = detect_suspicious_activity(all_entries)

    logger.info(
        f"Audit summary: {len(all_entries)} total entries | {len(suspicious)} suspicious"
    )
    return {
        "total": len(all_entries),
        "by_category": by_category,
        "by_outcome": by_outcome,
        "suspicious": suspicious,
    }


def detect_suspicious_activity(
    entries: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    suspicious: List[Dict[str, Any]] = []
    failed_by_actor: Dict[str, List[Dict[str, Any]]] = {}

    for entry in entries:
        outcome = str(entry.get("outcome", ""))
        actor = str(entry.get("actor", ""))
        timestamp_str = str(entry.get("timestamp", ""))

        if outcome == "failure":
            if actor not in failed_by_actor:
                failed_by_actor[actor] = []
            failed_by_actor[actor].append(entry)

        if timestamp_str:
            try:
                ts = datetime.datetime.fromisoformat(timestamp_str)
                if ts.hour < 6 or ts.hour >= 22:
                    suspicious.append({**entry, "suspicious_reason": "off_hours_access"})
            except Exception:
                pass

    for actor, failed_entries in failed_by_actor.items():
        if len(failed_entries) > 3:
            for e in failed_entries:
                suspicious.append({**e, "suspicious_reason": "repeated_failures"})

    logger.info(f"Suspicious activity detected: {len(suspicious)} entries")
    return suspicious


def run_audit_management(bucket: str) -> Dict[str, Any]:
    date = datetime.datetime.utcnow().strftime("%Y/%m/%d")
    summary = generate_audit_summary(bucket, date)

    logger.info("Audit Management Complete")
    return summary


if __name__ == "__main__":
    pass
