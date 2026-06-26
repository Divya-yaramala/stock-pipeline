import datetime
from unittest.mock import MagicMock, patch

from ingestion.workflow_manager import (
    get_due_workflows,
    parse_cron_schedule,
    run_workflow_check,
    trigger_workflow,
)


def test_parse_cron_schedule_valid():
    result = parse_cron_schedule("0 6 * * 1-5")
    assert isinstance(result, dict)
    assert result["hour"] == "6"
    assert result["minute"] == "0"
    assert result["weekday"] == "1-5"


def test_parse_cron_continuous():
    result = parse_cron_schedule("continuous")
    assert result == {"schedule": "continuous"}


def test_trigger_workflow_success():
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {}
    with patch("ingestion.workflow_manager.boto3.client", return_value=mock_s3):
        result = trigger_workflow("W001", "test-bucket")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_get_due_workflows_returns_list():
    current_time = datetime.datetime(2026, 6, 23, 6, 0, 0)  # Tuesday 6 AM UTC
    result = get_due_workflows(current_time)
    assert isinstance(result, list)


def test_run_workflow_check_structure():
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {}
    with patch("ingestion.workflow_manager.boto3.client", return_value=mock_s3):
        with patch("ingestion.workflow_manager.get_due_workflows", return_value=[]):
            result = run_workflow_check("test-bucket")
    assert isinstance(result, dict)
    assert "triggered" in result
    assert "workflows" in result
