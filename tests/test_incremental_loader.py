import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from ingestion.incremental_loader import (
    detect_data_gaps,
    get_last_loaded_date,
    run_incremental_load,
    save_watermark,
)


def test_get_last_loaded_date_found():
    payload = json.dumps({"last_loaded_date": "2026-01-15"}).encode("utf-8")
    with patch("ingestion.incremental_loader.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.return_value = {"Body": BytesIO(payload)}
        result = get_last_loaded_date("AAPL", "test-bucket")
    assert result == "2026-01-15"


def test_get_last_loaded_date_not_found():
    with patch("ingestion.incremental_loader.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.side_effect = Exception("NoSuchKey")
        result = get_last_loaded_date("AAPL", "test-bucket")
    assert result is None


def test_save_watermark_success():
    with patch("ingestion.incremental_loader.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        result = save_watermark("AAPL", "2026-01-15", "test-bucket")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_detect_data_gaps_finds_gaps():
    with patch("ingestion.incremental_loader.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.head_object.side_effect = Exception("NoSuchKey")
        result = detect_data_gaps("AAPL", "test-bucket", "2026-01-02", "2026-01-05")
    assert isinstance(result, list)
    assert len(result) > 0


def test_run_incremental_load_structure():
    with patch(
        "ingestion.incremental_loader.get_last_loaded_date", return_value="2026-01-01"
    ), patch("ingestion.incremental_loader.detect_data_gaps", return_value=["2026-01-02"]), patch(
        "ingestion.incremental_loader.load_incremental_data",
        return_value={"2026-01-02": {"close": 150.0}},
    ), patch(
        "ingestion.incremental_loader.save_watermark", return_value=True
    ):
        result = run_incremental_load(["AAPL"], "test-bucket")
    assert isinstance(result, dict)
    assert "tickers_updated" in result
