import datetime
import json
import logging
import os
import re

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET_PATTERNS = [
    ("aws_key", r"AKIA[0-9A-Z]{16}"),
    ("password", r'password\s*=\s*["\'][^"\']+["\']'),
    ("api_key", r'api_key\s*=\s*["\'][^"\']+["\']'),
    ("token", r'token\s*=\s*["\'][^"\']+["\']'),
]

SENSITIVE_ENV_VARS = [
    "AWS_SECRET_ACCESS_KEY",
    "DATABASE_PASSWORD",
    "API_KEY",
    "SECRET_KEY",
    "AUTH_TOKEN",
    "PRIVATE_KEY",
]


def scan_for_hardcoded_secrets(file_path: str) -> list:
    findings = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for line_num, line in enumerate(lines, start=1):
            for pattern_name, pattern in SECRET_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(
                        {
                            "file": file_path,
                            "line": line_num,
                            "pattern": pattern_name,
                            "snippet": line.strip()[:80],
                        }
                    )
        logger.info(f"Scan complete: {len(findings)} issues in {file_path}")
    except Exception as e:
        logger.error(f"Failed to scan {file_path}: {e}")
    return findings


def scan_directory(directory: str) -> dict:
    all_findings = []
    files_with_issues = 0
    total_files = 0
    try:
        for root, _, files in os.walk(directory):
            for fname in files:
                if fname.endswith(".py"):
                    total_files += 1
                    fpath = os.path.join(root, fname)
                    findings = scan_for_hardcoded_secrets(fpath)
                    if findings:
                        files_with_issues += 1
                        all_findings.extend(findings)
    except Exception as e:
        logger.error(f"Failed to scan directory {directory}: {e}")
    logger.info(
        f"Directory scan: {total_files} files, {files_with_issues} with issues, "
        f"{len(all_findings)} total findings"
    )
    return {
        "total_files": total_files,
        "files_with_issues": files_with_issues,
        "findings": all_findings,
    }


def check_env_vars_not_logged() -> list:
    violations = []
    for var_name in SENSITIVE_ENV_VARS:
        value = os.environ.get(var_name, "")
        if value:
            violations.append(
                {
                    "env_var": var_name,
                    "warning": "Sensitive env var is set — ensure it is never logged",
                }
            )
    logger.info("Env var log-safety check complete")
    return violations


def generate_security_report(scan_results: dict, bucket: str) -> bool:
    s3 = boto3.client("s3")
    try:
        now = datetime.datetime.utcnow()
        key = f"security/reports/{now.year:04d}/{now.month:02d}/{now.day:02d}/report.json"
        report = {
            "generated_at": now.isoformat(),
            "total_files": scan_results.get("total_files", 0),
            "files_with_issues": scan_results.get("files_with_issues", 0),
            "total_findings": len(scan_results.get("findings", [])),
            "findings": scan_results.get("findings", []),
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(report))
        logger.info(f"Security report saved: {key}")
        return True
    except Exception as e:
        logger.error(f"Failed to generate security report: {e}")
        return False


def run_security_scan(directory: str, bucket: str) -> dict:
    results = scan_directory(directory)
    generate_security_report(results, bucket)
    total = results["total_files"]
    issues = len(results["findings"])
    logger.info(f"{total} files scanned, {issues} issues found")
    return results


if __name__ == "__main__":
    pass
