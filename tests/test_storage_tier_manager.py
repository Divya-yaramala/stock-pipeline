"""Tests for ingestion/storage_tier_manager.py."""

from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from ingestion.storage_tier_manager import (
    STORAGE_TIERS,
    calculate_tier_costs,
    get_object_tier,
    move_to_tier,
    recommend_tier_changes,
)


def _make_s3_obj(
    key: str, days_old: int, storage_class: str = "STANDARD", size: int = 1024
) -> Dict[str, Any]:
    last_modified = MagicMock()
    last_modified.replace.return_value = datetime.utcnow() - timedelta(days=days_old)
    return {"Key": key, "LastModified": last_modified, "Size": size, "StorageClass": storage_class}


def test_storage_tiers_structure() -> None:
    assert set(STORAGE_TIERS.keys()) == {"HOT", "WARM", "COLD", "FROZEN"}
    for tier, info in STORAGE_TIERS.items():
        assert "storage_class" in info
        assert "cost_per_gb" in info
        assert info["cost_per_gb"] > 0


def test_get_object_tier() -> None:
    mock_client = MagicMock()
    last_modified = MagicMock()
    last_modified.replace.return_value = datetime.utcnow() - timedelta(days=10)
    mock_client.head_object.return_value = {
        "StorageClass": "STANDARD",
        "LastModified": last_modified,
    }

    with patch("ingestion.storage_tier_manager.boto3.client", return_value=mock_client):
        info = get_object_tier("bucket", "raw/stocks/file.json")

    assert info["tier"] == "HOT"
    assert info["storage_class"] == "STANDARD"
    assert info["age_days"] == 10


def test_move_to_tier_dry_run() -> None:
    result = move_to_tier("bucket", "raw/stocks/file.json", "COLD", dry_run=True)
    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["storage_class"] == "GLACIER"


def test_calculate_tier_costs() -> None:
    objects = [
        {"tier": "HOT", "size_bytes": 1024**3},
        {"tier": "COLD", "size_bytes": 1024**3},
    ]
    costs = calculate_tier_costs(objects)
    assert costs["cost_by_tier"]["HOT"] > costs["cost_by_tier"]["COLD"]
    assert costs["total_monthly_cost_usd"] > 0
    assert costs["count_by_tier"]["HOT"] == 1
    assert costs["count_by_tier"]["COLD"] == 1


def test_recommend_tier_changes() -> None:
    mock_client = MagicMock()
    paginator = MagicMock()
    paginator.paginate.return_value = [
        {
            "Contents": [
                _make_s3_obj("raw/stocks/old.json", 100),
                _make_s3_obj("raw/stocks/new.json", 5),
            ]
        }
    ]
    mock_client.get_paginator.return_value = paginator

    with patch("ingestion.storage_tier_manager.boto3.client", return_value=mock_client):
        recs = recommend_tier_changes("bucket", "raw/stocks")

    assert len(recs) == 1
    assert recs[0]["current_tier"] == "HOT"
    assert recs[0]["recommended_tier"] == "COLD"
