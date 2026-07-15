import datetime
import json
import logging
import re
from typing import Any, Dict, List

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PII_PATTERNS: Dict[str, str] = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
    "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
}

_HIGH_RISK_TYPES = {"ssn", "credit_card"}


def _mask_email_match(m: "re.Match[str]") -> str:
    full = m.group()
    local, _, rest = full.partition("@")
    tld = rest.rsplit(".", 1)[-1] if "." in rest else rest
    return f"{local[0] if local else '*'}***@***.{tld}"


def _mask_phone_match(m: "re.Match[str]") -> str:
    digits = re.sub(r"\D", "", m.group())
    return f"***-***-{digits[-4:]}"


def _mask_ssn_match(m: "re.Match[str]") -> str:
    digits = re.sub(r"\D", "", m.group())
    return f"***-**-{digits[-4:]}"


def scan_for_pii(data: Dict[str, Any]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    for field, value in data.items():
        if not isinstance(value, str):
            continue
        for pii_type, pattern in PII_PATTERNS.items():
            match = re.search(pattern, value)
            if match:
                findings.append(
                    {"field": field, "pii_type": pii_type, "pattern_matched": match.group()}
                )

    pii_found = len(findings) > 0
    if not pii_found:
        risk_level = "none"
    elif any(f["pii_type"] in _HIGH_RISK_TYPES for f in findings):
        risk_level = "high"
    else:
        risk_level = "low"

    logger.info(f"PII scan: pii_found={pii_found}, risk={risk_level}, findings={len(findings)}")
    return {"pii_found": pii_found, "findings": findings, "risk_level": risk_level}


def mask_pii(data: Dict[str, Any], mask_char: str = "*") -> Dict[str, Any]:
    masked: Dict[str, Any] = {}
    masked_fields: List[str] = []

    for field, value in data.items():
        if not isinstance(value, str):
            masked[field] = value
            continue

        original = value
        val = value
        val = re.sub(PII_PATTERNS["email"], _mask_email_match, val)
        val = re.sub(PII_PATTERNS["phone"], _mask_phone_match, val)
        val = re.sub(PII_PATTERNS["ssn"], _mask_ssn_match, val)
        val = re.sub(PII_PATTERNS["credit_card"], mask_char * 16, val)
        val = re.sub(PII_PATTERNS["ip_address"], mask_char * 8, val)

        masked[field] = val
        if val != original:
            masked_fields.append(field)

    logger.info(f"PII masked: {len(masked_fields)} fields masked")
    return masked


def scan_s3_file_for_pii(bucket: str, key: str) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read()
    try:
        data = json.loads(content)
    except Exception:
        data = {"raw_content": content.decode("utf-8", errors="replace")}
    result = scan_for_pii(data)
    logger.info(f"File scan complete: {key}")
    return result


def run_pii_scan(bucket: str, prefix: str) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    files_scanned = 0
    pii_found_count = 0
    all_findings: List[Dict[str, Any]] = []

    for obj in response.get("Contents", []):
        key = str(obj["Key"])
        result = scan_s3_file_for_pii(bucket, key)
        files_scanned += 1
        if result["pii_found"]:
            pii_found_count += 1
            all_findings.extend(result["findings"])

    now = datetime.datetime.utcnow()
    date_path = now.strftime("%Y/%m/%d")
    report: Dict[str, Any] = {
        "files_scanned": files_scanned,
        "pii_found": pii_found_count,
        "findings": all_findings,
        "prefix": prefix,
        "scanned_at": now.isoformat(),
    }
    s3.put_object(
        Bucket=bucket,
        Key=f"security/pii_scan/{date_path}/report.json",
        Body=json.dumps(report),
    )
    logger.info(f"PII scan summary: {files_scanned} files, {pii_found_count} with PII")
    return report


if __name__ == "__main__":
    pass
