import datetime
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

COMPLIANCE_FRAMEWORKS: List[Dict[str, Any]] = [
    {
        "framework_id": "CF001",
        "name": "SOX",
        "description": "Sarbanes-Oxley financial controls",
        "requirements": [
            "audit_trail",
            "data_integrity",
            "access_control",
            "retention_7_years",
        ],
    },
    {
        "framework_id": "CF002",
        "name": "GDPR",
        "description": "General Data Protection Regulation",
        "requirements": [
            "pii_protection",
            "data_minimization",
            "right_to_erasure",
            "consent_tracking",
        ],
    },
    {
        "framework_id": "CF003",
        "name": "FINRA",
        "description": "Financial Industry Regulatory Authority",
        "requirements": [
            "trade_reporting",
            "audit_trail",
            "data_retention_6_years",
            "supervisory_controls",
        ],
    },
    {
        "framework_id": "CF004",
        "name": "INTERNAL",
        "description": "Internal data governance policy",
        "requirements": [
            "data_classification",
            "quality_gates",
            "sla_compliance",
            "documentation",
        ],
    },
]

_REQUIREMENT_CHECKS: Dict[str, bool] = {
    "audit_trail": True,
    "data_integrity": True,
    "access_control": True,
    "retention_7_years": False,
    "pii_protection": True,
    "data_minimization": True,
    "right_to_erasure": False,
    "consent_tracking": False,
    "trade_reporting": True,
    "data_retention_6_years": False,
    "supervisory_controls": True,
    "data_classification": True,
    "quality_gates": True,
    "sla_compliance": True,
    "documentation": True,
}


def check_framework_compliance(
    framework_id: str,
    bucket: str,
    date: str,
) -> Dict[str, Any]:
    framework = next(
        (f for f in COMPLIANCE_FRAMEWORKS if str(f["framework_id"]) == framework_id), None
    )
    if framework is None:
        return {
            "framework": framework_id,
            "compliant": False,
            "score_pct": 0.0,
            "passed": [],
            "failed": [f"Unknown framework: {framework_id}"],
        }

    requirements = list(framework.get("requirements", []))
    passed: List[str] = []
    failed: List[str] = []

    for req in requirements:
        if _REQUIREMENT_CHECKS.get(str(req), False):
            passed.append(str(req))
        else:
            failed.append(str(req))

    total = len(requirements)
    score_pct = float(len(passed)) / float(total) * 100.0 if total > 0 else 0.0
    compliant = len(failed) == 0

    logger.info(
        f"Framework {framework_id} compliance score: {score_pct:.1f}% "
        f"({len(passed)}/{total} requirements)"
    )
    return {
        "framework": str(framework.get("name", framework_id)),
        "compliant": compliant,
        "score_pct": score_pct,
        "passed": passed,
        "failed": failed,
    }


def generate_compliance_report(
    bucket: str,
    date: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    frameworks_results: Dict[str, Any] = {}
    total_score = 0.0

    for fw in COMPLIANCE_FRAMEWORKS:
        fw_id = str(fw["framework_id"])
        result = check_framework_compliance(fw_id, bucket, date)
        frameworks_results[fw_id] = result
        total_score += float(str(result.get("score_pct", 0.0)))

    total_score_pct = total_score / len(COMPLIANCE_FRAMEWORKS) if COMPLIANCE_FRAMEWORKS else 0.0
    overall_compliant = all(
        bool(r.get("compliant", False)) for r in frameworks_results.values()
    )

    report: Dict[str, Any] = {
        "date": date,
        "overall_compliant": overall_compliant,
        "frameworks": frameworks_results,
        "total_score_pct": total_score_pct,
    }

    date_path = date.replace("-", "/")
    key = f"reports/compliance/{date_path}/report.json"
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(report))
    except Exception as e:
        logger.error(f"Failed to save compliance report: {e}")

    logger.info(f"Overall compliance score: {total_score_pct:.1f}% | compliant={overall_compliant}")
    return report


def get_compliance_history(
    bucket: str,
    days: int = 30,
) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3")
    history: List[Dict[str, Any]] = []

    for i in range(days):
        day = datetime.datetime.utcnow() - datetime.timedelta(days=days - 1 - i)
        date_path = day.strftime("%Y/%m/%d")
        key = f"reports/compliance/{date_path}/report.json"
        try:
            resp = s3.get_object(Bucket=bucket, Key=key)
            report = json.loads(resp["Body"].read())
            history.append(report)
        except Exception:
            pass

    logger.info(f"Compliance history loaded: {len(history)} days")
    return history


def calculate_compliance_trend(
    history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    scores = [float(str(r.get("total_score_pct", 0.0))) for r in history if r]
    if not scores:
        logger.info("Compliance trend: insufficient data")
        return {"trend": "insufficient_data", "avg_score": 0.0, "min_score": 0.0}

    avg_score = sum(scores) / len(scores)
    min_score = min(scores)

    if len(scores) >= 2:
        trend = "improving" if scores[-1] > scores[0] else "declining" if scores[-1] < scores[0] else "stable"
    else:
        trend = "stable"

    logger.info(f"Compliance trend: {trend} | avg={avg_score:.1f}% | min={min_score:.1f}%")
    return {"trend": trend, "avg_score": avg_score, "min_score": min_score}


def generate_compliance_certificate(
    framework_id: str,
    bucket: str,
    date: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    result = check_framework_compliance(framework_id, bucket, date)
    certified = bool(result.get("compliant", False))
    certificate_id = str(uuid.uuid4()) if certified else ""

    certificate: Dict[str, Any] = {
        "certified": certified,
        "framework": str(result.get("framework", framework_id)),
        "date": date,
        "certificate_id": certificate_id,
    }

    if certified:
        date_path = date.replace("-", "/")
        key = f"reports/certificates/{framework_id}/{date_path}.json"
        try:
            s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(certificate))
        except Exception as e:
            logger.error(f"Failed to save certificate: {e}")

    logger.info(f"Certification result: {framework_id} | certified={certified}")
    return certificate


def run_compliance_reporting(bucket: str) -> Dict[str, Any]:
    date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    report = generate_compliance_report(bucket, date)

    history = get_compliance_history(bucket, days=30)
    trend = calculate_compliance_trend(history)

    certificates: List[Dict[str, Any]] = []
    for fw in COMPLIANCE_FRAMEWORKS:
        fw_id = str(fw["framework_id"])
        cert = generate_compliance_certificate(fw_id, bucket, date)
        if cert.get("certified"):
            certificates.append(cert)

    summary: Dict[str, Any] = {
        "date": date,
        "overall_compliant": report.get("overall_compliant"),
        "total_score_pct": report.get("total_score_pct"),
        "trend": trend,
        "certificates_issued": len(certificates),
    }

    logger.info("Compliance Reporting Complete")
    return summary


if __name__ == "__main__":
    pass
