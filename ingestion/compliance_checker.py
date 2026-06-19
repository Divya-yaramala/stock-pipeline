import json
import logging
from datetime import datetime

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COMPLIANCE_RULES = [
    {"rule": "data_classification_required", "description": "All datasets must be classified"},
    {"rule": "audit_log_enabled", "description": "All data access must be logged"},
    {"rule": "retention_policy_defined", "description": "All datasets must have retention policy"},
    {"rule": "no_pii_in_raw_layer", "description": "Raw S3 data must not contain PII"},
    {"rule": "encryption_at_rest", "description": "All S3 data must be encrypted"},
]

PII_FIELDS = {"email", "phone", "ssn", "dob", "name", "address"}


def check_encryption(bucket: str) -> bool:
    s3 = boto3.client("s3")
    try:
        s3.get_bucket_encryption(Bucket=bucket)
        logger.info("check_encryption: bucket=%s encrypted=True", bucket)
        return True
    except Exception:
        logger.info("check_encryption: bucket=%s encrypted=False", bucket)
        return False


def check_no_pii_in_raw(bucket: str, date: str) -> dict:
    s3 = boto3.client("s3")
    date_path = date.replace("-", "/")
    prefix = f"raw/stocks/{date_path}/"
    violations = []

    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        for obj in response.get("Contents", []):
            try:
                data = s3.get_object(Bucket=bucket, Key=obj["Key"])
                content = json.loads(data["Body"].read().decode("utf-8"))
                if isinstance(content, dict):
                    keys = {k.lower() for k in content.keys()}
                    found = keys & PII_FIELDS
                    if found:
                        violations.append(f"{obj['Key']}: PII fields detected: {sorted(found)}")
            except Exception:
                pass
    except Exception as e:
        logger.error("PII check failed: %s", e)

    compliant = len(violations) == 0
    logger.info(
        "check_no_pii_in_raw: date=%s compliant=%s violations=%d",
        date,
        compliant,
        len(violations),
    )
    return {"compliant": compliant, "violations": violations}


def check_audit_logs_present(bucket: str, date: str) -> bool:
    s3 = boto3.client("s3")
    date_path = date.replace("-", "/")
    prefix = f"governance/audit/{date_path}/"
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        present = len(response.get("Contents", [])) > 0
        logger.info("check_audit_logs_present: date=%s present=%s", date, present)
        return present
    except Exception as e:
        logger.error("Audit log check failed: %s", e)
        return False


def run_compliance_check(bucket: str) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    violations = []
    checks_passed = 0
    total_checks = len(COMPLIANCE_RULES)

    if check_encryption(bucket):
        checks_passed += 1
    else:
        violations.append("encryption_at_rest: bucket encryption not enabled")

    pii_result = check_no_pii_in_raw(bucket, today)
    if pii_result["compliant"]:
        checks_passed += 1
    else:
        violations.extend([f"no_pii_in_raw_layer: {v}" for v in pii_result["violations"]])

    if check_audit_logs_present(bucket, today):
        checks_passed += 1
    else:
        violations.append("audit_log_enabled: no audit logs found for today")

    s3 = boto3.client("s3")
    for rule_prefix, rule_name in [
        ("governance/classification/", "data_classification_required"),
        ("governance/retention/", "retention_policy_defined"),
    ]:
        try:
            resp = s3.list_objects_v2(Bucket=bucket, Prefix=rule_prefix)
            if resp.get("Contents"):
                checks_passed += 1
            else:
                violations.append(f"{rule_name}: no records found")
        except Exception as e:
            logger.warning("Could not check %s: %s", rule_name, e)
            violations.append(f"{rule_name}: check failed")

    score_pct = round(checks_passed / total_checks * 100, 1) if total_checks > 0 else 0.0
    compliant = len(violations) == 0

    logger.info("Compliance check: score=%.1f%%, compliant=%s", score_pct, compliant)
    return {
        "compliant": compliant,
        "score_pct": score_pct,
        "violations": violations,
    }


if __name__ == "__main__":
    pass
