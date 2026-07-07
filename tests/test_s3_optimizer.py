from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from ingestion.s3_optimizer import (
    calculate_cost_savings,
    calculate_prefix_size,
    delete_expired_objects,
    identify_expired_objects,
    run_s3_optimization,
)


def _make_obj(key: str, size: int, days_old: int) -> dict:
    return {
        "Key": key,
        "Size": size,
        "LastModified": datetime.now(timezone.utc) - timedelta(days=days_old),
    }


def test_calculate_prefix_size_structure():
    page = {"Contents": [_make_obj("raw/stocks/a.json", 1024, 10)]}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    s3 = MagicMock()
    s3.get_paginator.return_value = paginator

    with patch("ingestion.s3_optimizer.boto3.client", return_value=s3):
        result = calculate_prefix_size("my-bucket", "raw/stocks")

    assert "total_size_mb" in result
    assert "object_count" in result
    assert result["object_count"] == 1


def test_identify_expired_objects_finds_old():
    page = {"Contents": [_make_obj("raw/stocks/old.json", 512, 100)]}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    s3 = MagicMock()
    s3.get_paginator.return_value = paginator

    with patch("ingestion.s3_optimizer.boto3.client", return_value=s3):
        expired = identify_expired_objects("my-bucket", "raw/stocks", retention_days=90)

    assert len(expired) > 0
    assert "raw/stocks/old.json" in expired


def test_delete_expired_objects_dry_run():
    s3 = MagicMock()
    keys = ["raw/stocks/a.json", "raw/stocks/b.json"]

    with patch("ingestion.s3_optimizer.boto3.client", return_value=s3):
        result = delete_expired_objects("my-bucket", keys, dry_run=True)

    assert result["dry_run"] is True
    assert result["deleted"] == 0
    s3.delete_objects.assert_not_called()


def test_calculate_cost_savings_delete():
    result = calculate_cost_savings(size_gb=10.0, action="delete")

    assert "monthly_savings" in result
    assert "annual_savings" in result
    assert result["monthly_savings"] > 0
    assert result["annual_savings"] > result["monthly_savings"]


def test_run_s3_optimization_structure():
    page: dict = {"Contents": []}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    s3 = MagicMock()
    s3.get_paginator.return_value = paginator

    with patch("ingestion.s3_optimizer.boto3.client", return_value=s3):
        result = run_s3_optimization("my-bucket", dry_run=True)

    assert "dry_run" in result
    assert "total_expired" in result
    assert "total_deleted" in result
    assert "estimated_savings" in result
    assert result["dry_run"] is True
