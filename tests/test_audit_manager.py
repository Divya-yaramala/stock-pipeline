import json
from unittest.mock import MagicMock, patch

import pytest

from ingestion.audit_manager import (
    create_audit_entry,
    detect_suspicious_activity,
    generate_audit_summary,
    save_audit_entry,
)


def _make_s3_body(data: dict) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return body


def test_create_audit_entry_structure():
    result = create_audit_entry(
        category="data_access",
        action="read_stock_prices",
        actor="analytics_team",
        resource="raw/stocks/AAPL",
    )
    assert isinstance(result, dict)
    assert "audit_id" in result
    assert "category" in result
    assert result["category"] == "data_access"
    assert result["outcome"] == "success"


def test_create_audit_entry_invalid_category():
    with pytest.raises(ValueError):
        create_audit_entry(
            category="not_a_real_category",
            action="read",
            actor="someone",
            resource="raw/stocks",
        )


def test_save_audit_entry_success():
    entry = create_audit_entry(
        category="pipeline_execution",
        action="run_pipeline",
        actor="airflow",
        resource="dag/stock_pipeline",
    )
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.audit_manager.boto3.client", return_value=mock_client):
        result = save_audit_entry(entry, "test-bucket")
    assert result is True
    mock_client.put_object.assert_called_once()


def test_detect_suspicious_activity_finds_failed():
    entries = [
        {
            "audit_id": f"id-{i}",
            "actor": "bad_actor",
            "outcome": "failure",
            "category": "data_access",
            "timestamp": "2026-07-28T14:00:00",
        }
        for i in range(4)
    ]
    result = detect_suspicious_activity(entries)
    assert isinstance(result, list)
    assert len(result) > 0


def test_generate_audit_summary_structure():
    entry = {
        "audit_id": "abc-123",
        "category": "data_access",
        "action": "read",
        "actor": "analyst",
        "outcome": "success",
        "timestamp": "2026-07-28T10:00:00",
    }
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [{"Key": "audit/entries/2026/07/28/data_access/abc-123.json"}]
    }
    mock_client.get_object.return_value = {"Body": _make_s3_body(entry)}
    with patch("ingestion.audit_manager.boto3.client", return_value=mock_client):
        result = generate_audit_summary("test-bucket", "2026/07/28")
    assert isinstance(result, dict)
    assert "total" in result
    assert "by_category" in result
    assert "by_outcome" in result
    assert "suspicious" in result
