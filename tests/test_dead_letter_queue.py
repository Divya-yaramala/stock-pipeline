from unittest.mock import MagicMock, patch

from ingestion.dead_letter_queue import get_dlq_records, replay_dlq_record, send_to_dlq


@patch("ingestion.dead_letter_queue.boto3.client")
def test_send_to_dlq_success(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    mock_s3.put_object.return_value = {}
    result = send_to_dlq("test error", "AAPL", "fetch", {"price": 100}, "test-bucket")
    assert result is True


@patch("ingestion.dead_letter_queue.boto3.client")
def test_send_to_dlq_failure(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    mock_s3.put_object.side_effect = Exception("S3 error")
    result = send_to_dlq("test error", "AAPL", "fetch", {}, "test-bucket")
    assert result is False


@patch("ingestion.dead_letter_queue.boto3.client")
def test_send_to_dlq_correct_s3_path(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    mock_s3.put_object.return_value = {}
    send_to_dlq("error", "AAPL", "fetch", {}, "test-bucket")
    key = mock_s3.put_object.call_args[1]["Key"]
    assert "errors/" in key
    assert "/fetch/" in key
    assert "AAPL" in key


@patch("ingestion.dead_letter_queue.boto3.client")
def test_get_dlq_records_success(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "errors/2026/05/22/fetch/AAPL_20260522_180000.json"}]
    }
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=b'{"ticker": "AAPL", "step": "fetch"}'))
    }
    result = get_dlq_records("test-bucket", "2026/05/22")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["ticker"] == "AAPL"


@patch("ingestion.dead_letter_queue.boto3.client")
def test_get_dlq_records_empty(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    mock_s3.list_objects_v2.return_value = {}
    result = get_dlq_records("test-bucket", "2026/05/22")
    assert result == []


@patch("ingestion.fetch_stocks.run_pipeline")
def test_replay_dlq_record_routes_correctly(mock_run_pipeline):
    record = {"step": "fetch", "ticker": "AAPL", "error": "test error", "payload": {}}
    result = replay_dlq_record(record)
    mock_run_pipeline.assert_called_once()
    assert result is True
