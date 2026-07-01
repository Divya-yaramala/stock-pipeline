import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

from ingestion.lineage_tracker import find_impacted_datasets

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def analyze_schema_change_impact(
    dataset_name: str,
    changed_fields: List[str],
    bucket: str,
) -> Dict[str, Any]:
    impacted = find_impacted_datasets(dataset_name, bucket)
    count = len(impacted)

    if count < 3:
        severity = "low"
    elif count < 7:
        severity = "medium"
    else:
        severity = "high"

    result: Dict[str, Any] = {
        "impacted_count": count,
        "datasets": impacted,
        "severity": severity,
        "changed_fields": changed_fields,
        "source_dataset": dataset_name,
    }
    logger.info(
        "Schema change impact for %s: %d datasets affected, severity=%s",
        dataset_name,
        count,
        severity,
    )
    return result


def analyze_data_quality_impact(
    dataset_name: str,
    quality_score: float,
    bucket: str,
) -> Dict[str, Any]:
    affected: List[str] = []
    risk_level = "none"

    if quality_score < 80:
        affected = find_impacted_datasets(dataset_name, bucket)

        if quality_score < 70:
            risk_level = "high"
        elif quality_score < 75:
            risk_level = "medium"
        else:
            risk_level = "low"

    result: Dict[str, Any] = {
        "risk_level": risk_level,
        "affected_datasets": affected,
        "quality_score": quality_score,
        "dataset": dataset_name,
    }
    logger.info(
        "Quality impact for %s (score=%.1f): risk=%s, %d datasets affected",
        dataset_name,
        quality_score,
        risk_level,
        len(affected),
    )
    return result


def generate_impact_report(
    trigger: str,
    dataset: str,
    bucket: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    now = datetime.now()
    date_path = now.strftime("%Y/%m/%d")

    impacted = find_impacted_datasets(dataset, bucket)

    report: Dict[str, Any] = {
        "trigger": trigger,
        "dataset": dataset,
        "generated_at": now.isoformat(),
        "impacted_datasets": impacted,
        "impacted_count": len(impacted),
    }

    if trigger == "schema_change":
        count = len(impacted)
        report["severity"] = "high" if count >= 7 else ("medium" if count >= 3 else "low")
    elif trigger == "quality_drop":
        report["risk_level"] = "high"
    elif trigger == "pipeline_failure":
        report["cascading_risk"] = "high" if len(impacted) > 0 else "none"

    key = f"lineage/impact/{date_path}/report.json"
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(report))
    return report


def run_impact_analysis(
    bucket: str,
    date: str,
    datasets: Optional[List[str]] = None,
) -> Dict[str, Any]:
    key_datasets = datasets or [
        "raw_prices",
        "validated_prices",
        "postgres_staging",
        "snowflake_raw",
        "snowflake_marts",
    ]

    combined: Dict[str, Any] = {
        "date": date,
        "analyses": {},
        "total_impacted": 0,
    }

    for dataset in key_datasets:
        impacted = find_impacted_datasets(dataset, bucket)
        combined["analyses"][dataset] = {
            "impacted_count": len(impacted),
            "impacted_datasets": impacted,
        }
        combined["total_impacted"] += len(impacted)

    logger.info("Impact analysis complete for %d key datasets", len(key_datasets))
    return combined


if __name__ == "__main__":
    pass
