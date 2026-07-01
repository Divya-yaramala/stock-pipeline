import json
import re
from unittest.mock import MagicMock, patch

from ingestion.lineage_tracker import (
    find_impacted_datasets,
    generate_lineage_report,
    get_dataset_lineage,
    record_lineage_event,
)


def test_record_lineage_event_success():
    with patch("ingestion.lineage_tracker.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        result = record_lineage_event(
            source_dataset="yahoo_finance",
            target_dataset="raw_prices",
            transformation="ingestion",
            ticker="AAPL",
            bucket="test-bucket",
        )
    assert isinstance(result, str)
    assert len(result) > 0


def test_record_lineage_event_correct_path():
    with patch("ingestion.lineage_tracker.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        record_lineage_event(
            source_dataset="raw_prices",
            target_dataset="validated_prices",
            transformation="validation",
            ticker="MSFT",
            bucket="test-bucket",
        )
    key = mock_s3.put_object.call_args[1]["Key"]
    assert re.match(r"lineage/\d{4}/\d{2}/\d{2}/", key)


def test_get_dataset_lineage_structure():
    sample_record = {
        "lineage_id": "abc123",
        "source_dataset": "yahoo_finance",
        "target_dataset": "raw_prices",
        "transformation": "ingestion",
        "ticker": "AAPL",
        "metadata": {},
        "recorded_at": "2026-07-01T10:00:00",
    }
    with patch("ingestion.lineage_tracker.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "lineage/2026/07/01/abc123.json"}]
        }
        mock_s3.get_object.return_value = {
            "Body": MagicMock(
                read=MagicMock(return_value=json.dumps(sample_record).encode("utf-8"))
            )
        }
        mock_boto3.client.return_value = mock_s3
        result = get_dataset_lineage("raw_prices", "test-bucket")
    assert "upstream" in result
    assert "downstream" in result


def test_find_impacted_datasets_returns_list():
    sample_record = {
        "lineage_id": "abc123",
        "source_dataset": "raw_prices",
        "target_dataset": "validated_prices",
        "transformation": "validation",
        "ticker": "AAPL",
        "metadata": {},
        "recorded_at": "2026-07-01T10:00:00",
    }
    with patch("ingestion.lineage_tracker.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "lineage/2026/07/01/abc123.json"}]
        }
        mock_s3.get_object.return_value = {
            "Body": MagicMock(
                read=MagicMock(return_value=json.dumps(sample_record).encode("utf-8"))
            )
        }
        mock_boto3.client.return_value = mock_s3
        result = find_impacted_datasets("raw_prices", "test-bucket")
    assert isinstance(result, list)


def test_generate_lineage_report_structure():
    sample_record = {
        "lineage_id": "abc123",
        "source_dataset": "yahoo_finance",
        "target_dataset": "raw_prices",
        "transformation": "ingestion",
        "ticker": "AAPL",
        "metadata": {},
        "recorded_at": "2026-07-01T10:00:00",
    }
    with patch("ingestion.lineage_tracker.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "lineage/2026/07/01/abc123.json"}]
        }
        mock_s3.get_object.return_value = {
            "Body": MagicMock(
                read=MagicMock(return_value=json.dumps(sample_record).encode("utf-8"))
            )
        }
        mock_boto3.client.return_value = mock_s3
        result = generate_lineage_report("test-bucket", "2026/07/01")
    assert "total_events" in result
