import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from ingestion.pipeline_scheduler import (
    create_schedule,
    disable_schedule,
    get_schedule,
    update_schedule,
)


def test_create_schedule_success():
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {}
    with patch("ingestion.pipeline_scheduler.boto3.client", return_value=mock_s3):
        result = create_schedule("daily_run", "0 6 * * 1-5", ["fetch", "validate"], "test-bucket")
    assert isinstance(result, str)
    assert len(result) > 0
    mock_s3.put_object.assert_called_once()


def test_get_schedule_success():
    payload = json.dumps(
        {"name": "daily_run", "status": "active", "cron_expr": "0 6 * * 1-5"}
    ).encode()
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": BytesIO(payload)}
    with patch("ingestion.pipeline_scheduler.boto3.client", return_value=mock_s3):
        result = get_schedule("daily_run", "test-bucket")
    assert isinstance(result, dict)
    assert result["name"] == "daily_run"


def test_get_schedule_not_found():
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = Exception("NoSuchKey")
    with patch("ingestion.pipeline_scheduler.boto3.client", return_value=mock_s3):
        result = get_schedule("missing_schedule", "test-bucket")
    assert result == {}


def test_disable_schedule_success():
    payload = json.dumps(
        {"name": "daily_run", "status": "active", "cron_expr": "0 6 * * 1-5"}
    ).encode()
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": BytesIO(payload)}
    mock_s3.put_object.return_value = {}
    with patch("ingestion.pipeline_scheduler.boto3.client", return_value=mock_s3):
        result = disable_schedule("daily_run", "test-bucket")
    assert result is True


def test_update_schedule_success():
    payload = json.dumps(
        {"name": "daily_run", "status": "active", "cron_expr": "0 6 * * 1-5"}
    ).encode()
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": BytesIO(payload)}
    mock_s3.put_object.return_value = {}
    with patch("ingestion.pipeline_scheduler.boto3.client", return_value=mock_s3):
        result = update_schedule("daily_run", {"cron_expr": "0 7 * * 1-5"}, "test-bucket")
    assert result is True
