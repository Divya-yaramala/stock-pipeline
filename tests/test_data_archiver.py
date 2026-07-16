"""Tests for ingestion/data_archiver.py."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from ingestion.data_archiver import (
    ARCHIVE_POLICIES,
    archive_to_glacier,
    delete_expired_data,
    generate_archival_report,
    identify_archive_candidates,
)


def _make_s3_obj(key: str, days_old: int, storage_class: str = "STANDARD") -> Dict[str, Any]:
    last_modified = MagicMock()
    last_modified.replace.return_value = datetime.utcnow() - timedelta(days=days_old)
    return {"Key": key, "LastModified": last_modified, "Size": 1024, "StorageClass": storage_class}


def _make_s3_body(data: Any) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return body


def test_archive_policies_structure() -> None:
    assert len(ARCHIVE_POLICIES) == 6
    for policy in ARCHIVE_POLICIES:
        assert "prefix" in policy
        assert "archive_after_days" in policy
        assert "delete_after_days" in policy
        assert policy["delete_after_days"] > policy["archive_after_days"]


def test_identify_archive_candidates() -> None:
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

    with patch("ingestion.data_archiver.boto3.client", return_value=mock_client):
        candidates = identify_archive_candidates("bucket", "raw/stocks", 90)

    assert len(candidates) == 1
    assert candidates[0]["key"] == "raw/stocks/old.json"


def test_archive_to_glacier_dry_run() -> None:
    objects = [{"key": "raw/stocks/file.json", "size_bytes": 1024}]
    result = archive_to_glacier("bucket", objects, dry_run=True)
    assert result["dry_run"] is True
    assert result["archived_count"] == 1
    assert "raw/stocks/file.json" in result["archived_keys"]


def test_delete_expired_data_dry_run() -> None:
    objects = [{"key": "raw/stocks/expired.json", "size_bytes": 512}]
    result = delete_expired_data("bucket", objects, dry_run=True)
    assert result["dry_run"] is True
    assert result["deleted_count"] == 1
    assert "raw/stocks/expired.json" in result["deleted_keys"]


def test_generate_archival_report() -> None:
    mock_client = MagicMock()
    archive_results = [{"archived_count": 3, "prefix": "raw/stocks"}]
    delete_results = [{"deleted_count": 1, "prefix": "raw/stocks"}]

    with patch("ingestion.data_archiver.boto3.client", return_value=mock_client):
        report = generate_archival_report("bucket", archive_results, delete_results)

    assert report["total_archived"] == 3
    assert report["total_deleted"] == 1
    mock_client.put_object.assert_called_once()
