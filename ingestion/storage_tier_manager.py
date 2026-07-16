"""Storage tier manager — cost-aware S3 tier recommendations and moves."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

logger = logging.getLogger(__name__)

STORAGE_TIERS: Dict[str, Dict[str, Any]] = {
    "HOT": {
        "storage_class": "STANDARD",
        "cost_per_gb": 0.023,
        "min_storage_days": 0,
        "description": "Frequently accessed data",
    },
    "WARM": {
        "storage_class": "STANDARD_IA",
        "cost_per_gb": 0.0125,
        "min_storage_days": 30,
        "description": "Infrequently accessed data",
    },
    "COLD": {
        "storage_class": "GLACIER",
        "cost_per_gb": 0.004,
        "min_storage_days": 90,
        "description": "Archival data — retrieval in minutes",
    },
    "FROZEN": {
        "storage_class": "DEEP_ARCHIVE",
        "cost_per_gb": 0.00099,
        "min_storage_days": 180,
        "description": "Deep archival — retrieval in hours",
    },
}

_CLASS_TO_TIER: Dict[str, str] = {
    "STANDARD": "HOT",
    "STANDARD_IA": "WARM",
    "GLACIER": "COLD",
    "DEEP_ARCHIVE": "FROZEN",
}


def get_object_tier(bucket: str, key: str) -> Dict[str, Any]:
    """Return the current tier info for a single S3 object."""
    s3 = boto3.client("s3")
    response = s3.head_object(Bucket=bucket, Key=key)
    storage_class: str = response.get("StorageClass", "STANDARD")
    tier_name = _CLASS_TO_TIER.get(storage_class, "HOT")
    tier_info: Dict[str, Any] = STORAGE_TIERS[tier_name]
    last_modified: datetime = response["LastModified"].replace(tzinfo=None)
    age_days = (datetime.utcnow() - last_modified).days
    return {
        "key": key,
        "tier": tier_name,
        "storage_class": storage_class,
        "cost_per_gb": float(tier_info["cost_per_gb"]),
        "age_days": age_days,
        "last_modified": last_modified.isoformat(),
    }


def move_to_tier(bucket: str, key: str, target_tier: str, dry_run: bool = True) -> Dict[str, Any]:
    """Move an S3 object to the target tier. Skips actual copy when dry_run=True."""
    if target_tier not in STORAGE_TIERS:
        return {"success": False, "error": f"Unknown tier: {target_tier}"}

    tier_info: Dict[str, Any] = STORAGE_TIERS[target_tier]
    storage_class: str = str(tier_info["storage_class"])

    if dry_run:
        return {
            "key": key,
            "target_tier": target_tier,
            "storage_class": storage_class,
            "dry_run": True,
            "success": True,
        }

    s3 = boto3.client("s3")
    try:
        s3.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": key},
            Key=key,
            StorageClass=storage_class,
            MetadataDirective="COPY",
        )
        return {
            "key": key,
            "target_tier": target_tier,
            "storage_class": storage_class,
            "dry_run": False,
            "success": True,
        }
    except Exception as exc:
        return {"key": key, "target_tier": target_tier, "success": False, "error": str(exc)}


def calculate_tier_costs(objects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate monthly costs per tier for a list of objects."""
    tier_totals: Dict[str, float] = {t: 0.0 for t in STORAGE_TIERS}
    tier_counts: Dict[str, int] = {t: 0 for t in STORAGE_TIERS}

    for obj in objects:
        tier: str = str(obj.get("tier", "HOT"))
        size_bytes: int = int(obj.get("size_bytes", 0))
        size_gb = size_bytes / (1024**3)
        if tier in STORAGE_TIERS:
            tier_totals[tier] += size_gb * float(STORAGE_TIERS[tier]["cost_per_gb"])
            tier_counts[tier] += 1

    total_cost = sum(tier_totals.values())
    return {
        "cost_by_tier": {t: round(v, 6) for t, v in tier_totals.items()},
        "count_by_tier": tier_counts,
        "total_monthly_cost_usd": round(total_cost, 6),
    }


def recommend_tier_changes(bucket: str, prefix: str) -> List[Dict[str, Any]]:
    """List objects in prefix and suggest tier downgrades based on age."""
    s3 = boto3.client("s3")
    recommendations: List[Dict[str, Any]] = []
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key: str = obj["Key"]
            storage_class: str = obj.get("StorageClass", "STANDARD")
            last_modified: datetime = obj["LastModified"].replace(tzinfo=None)
            age_days = (datetime.utcnow() - last_modified).days
            current_tier = _CLASS_TO_TIER.get(storage_class, "HOT")

            recommended: Optional[str] = None
            if age_days >= 180 and current_tier in ("HOT", "WARM", "COLD"):
                recommended = "FROZEN"
            elif age_days >= 90 and current_tier in ("HOT", "WARM"):
                recommended = "COLD"
            elif age_days >= 30 and current_tier == "HOT":
                recommended = "WARM"

            if recommended:
                recommendations.append(
                    {
                        "key": key,
                        "current_tier": current_tier,
                        "recommended_tier": recommended,
                        "age_days": age_days,
                        "size_bytes": obj["Size"],
                        "potential_saving_usd": round(
                            (obj["Size"] / (1024**3))
                            * (
                                float(STORAGE_TIERS[current_tier]["cost_per_gb"])
                                - float(STORAGE_TIERS[recommended]["cost_per_gb"])
                            ),
                            8,
                        ),
                    }
                )

    return recommendations


def run_tier_optimization(bucket: str, prefix: str, dry_run: bool = True) -> Dict[str, Any]:
    """Apply all recommended tier changes for a prefix."""
    recommendations = recommend_tier_changes(bucket, prefix)
    results: List[Dict[str, Any]] = []
    total_savings = 0.0

    for rec in recommendations:
        result = move_to_tier(
            bucket, str(rec["key"]), str(rec["recommended_tier"]), dry_run=dry_run
        )
        result["potential_saving_usd"] = rec["potential_saving_usd"]
        total_savings += float(rec["potential_saving_usd"])
        results.append(result)

    report: Dict[str, Any] = {
        "prefix": prefix,
        "changes_recommended": len(recommendations),
        "changes_applied": len([r for r in results if r.get("success")]),
        "total_potential_saving_usd": round(total_savings, 6),
        "dry_run": dry_run,
        "results": results,
        "optimized_at": datetime.utcnow().isoformat(),
    }

    s3 = boto3.client("s3")
    today = datetime.utcnow().strftime("%Y/%m/%d")
    safe_prefix = prefix.replace("/", "_")
    key = f"reports/tier_optimization/{today}/{safe_prefix}.json"
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(report, indent=2),
        ContentType="application/json",
    )
    logger.info("Tier optimization report saved to s3://%s/%s", bucket, key)
    return report
