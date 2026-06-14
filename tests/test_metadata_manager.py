import json
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

from ingestion.metadata_manager import (
    add_data_contract,
    check_data_contracts,
    generate_catalog_report,
    set_data_owner,
    tag_dataset,
)

SAMPLE_ENTRY = {
    "dataset_id": "abc123",
    "dataset_name": "stock_prices_raw",
    "description": "Raw OHLCV data",
    "schema": {},
    "source": "yfinance",
    "owner": "data-engineering",
    "registered_at": "2026-06-14T00:00:00+00:00",
    "tags": [],
    "status": "active",
}


def _mock_s3_with_entry(entry=None):
    payload = json.dumps(entry or SAMPLE_ENTRY).encode()
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": BytesIO(payload)}
    return mock_s3


def test_tag_dataset_success():
    mock_s3 = _mock_s3_with_entry()
    with patch("ingestion.metadata_manager.boto3.client", return_value=mock_s3):
        result = tag_dataset("stock_prices_raw", ["pii-free", "financial"], "test-bucket")
    assert result is True
    mock_s3.put_object.assert_called_once()
    saved = json.loads(mock_s3.put_object.call_args.kwargs["Body"].decode())
    assert "pii-free" in saved["tags"]
    assert "financial" in saved["tags"]


def test_set_data_owner_success():
    mock_s3 = _mock_s3_with_entry()
    with patch("ingestion.metadata_manager.boto3.client", return_value=mock_s3):
        result = set_data_owner("stock_prices_raw", "alice", "data-engineering", "test-bucket")
    assert result is True
    saved = json.loads(mock_s3.put_object.call_args.kwargs["Body"].decode())
    assert saved["owner"] == "alice"
    assert saved["team"] == "data-engineering"


def test_add_data_contract_success():
    mock_s3 = _mock_s3_with_entry()
    contract = {"SLA": "daily", "freshness_sla_hours": 25, "quality_threshold_pct": 95.0}
    with patch("ingestion.metadata_manager.boto3.client", return_value=mock_s3):
        result = add_data_contract("stock_prices_raw", contract, "test-bucket")
    assert result is True
    saved = json.loads(mock_s3.put_object.call_args.kwargs["Body"].decode())
    assert "contract" in saved
    assert saved["contract"]["SLA"] == "daily"


def test_check_data_contracts_no_violations():
    recent = datetime.now(timezone.utc).isoformat()
    entry_with_contract = {
        **SAMPLE_ENTRY,
        "last_updated": recent,
        "quality_score": 99.0,
        "contract": {"freshness_sla_hours": 25, "quality_threshold_pct": 95.0},
    }
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "catalog/datasets/stock_prices_raw/metadata.json"}]
    }
    mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(entry_with_contract).encode())}
    with patch("ingestion.metadata_manager.boto3.client", return_value=mock_s3):
        violations = check_data_contracts("test-bucket")
    assert violations == []


def test_generate_catalog_report_structure():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "catalog/datasets/stock_prices_raw/metadata.json"}]
    }
    mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(SAMPLE_ENTRY).encode())}
    with patch("ingestion.metadata_manager.boto3.client", return_value=mock_s3):
        report = generate_catalog_report("test-bucket")
    assert "datasets" in report
    assert "total_datasets" in report
    assert "violations" in report
    assert report["total_datasets"] == 1
