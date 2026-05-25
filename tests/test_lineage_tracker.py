import json
import re
from unittest.mock import MagicMock, patch

from ingestion.lineage_tracker import (
    generate_lineage_report,
    get_lineage_for_ticker,
    record_lineage,
)


def test_record_lineage_success():
    with patch("ingestion.lineage_tracker.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        result = record_lineage(
            source="yahoo_finance_api",
            destination="s3_raw",
            ticker="AAPL",
            row_count=5,
            transformation="extract_ohlcv",
            bucket="test-bucket",
        )
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_record_lineage_failure():
    with patch("ingestion.lineage_tracker.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = Exception("S3 error")
        mock_boto3.client.return_value = mock_s3
        result = record_lineage(
            source="yahoo_finance_api",
            destination="s3_raw",
            ticker="AAPL",
            row_count=5,
            transformation="extract_ohlcv",
            bucket="test-bucket",
        )
    assert result is False


def test_record_lineage_correct_s3_path():
    with patch("ingestion.lineage_tracker.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        record_lineage(
            source="s3_raw",
            destination="s3_processed_anomalies",
            ticker="MSFT",
            row_count=10,
            transformation="isolation_forest",
            bucket="test-bucket",
        )
    key = mock_s3.put_object.call_args[1]["Key"]
    assert re.match(r"lineage/\d{4}/\d{2}/\d{2}/MSFT_", key)


def test_get_lineage_for_ticker_success():
    sample_record = {
        "source": "yahoo_finance_api",
        "destination": "s3_raw",
        "ticker": "GOOGL",
        "row_count": 1,
        "transformation": "extract_ohlcv",
        "recorded_at": "2026-05-25T10:00:00",
    }
    with patch("ingestion.lineage_tracker.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "lineage/2026/05/25/GOOGL_20260525_100000.json"}]
        }
        mock_s3.get_object.return_value = {
            "Body": MagicMock(
                read=MagicMock(return_value=json.dumps(sample_record).encode("utf-8"))
            )
        }
        mock_boto3.client.return_value = mock_s3
        result = get_lineage_for_ticker("GOOGL", "test-bucket", "2026/05/25")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["ticker"] == "GOOGL"


def test_get_lineage_for_ticker_empty():
    with patch("ingestion.lineage_tracker.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {"Contents": []}
        mock_boto3.client.return_value = mock_s3
        result = get_lineage_for_ticker("TSLA", "test-bucket", "2026/05/25")
    assert result == []


def test_generate_lineage_report_structure():
    with patch("ingestion.lineage_tracker.get_lineage_for_ticker", return_value=[]):
        report = generate_lineage_report("test-bucket", "2026/05/25")
    assert set(report.keys()) == {"AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"}
