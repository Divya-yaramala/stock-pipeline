import json
from unittest.mock import MagicMock, patch

from ingestion.event_workflow import (
    execute_workflow_action,
    find_matching_triggers,
    process_event,
    save_workflow_log,
)


def _make_s3_body(data: dict) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return body


def test_find_matching_triggers_found():
    result = find_matching_triggers("anomaly_detected")
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0]["event"] == "anomaly_detected"


def test_find_matching_triggers_not_found():
    result = find_matching_triggers("unknown_event")
    assert isinstance(result, list)
    assert len(result) == 0


def test_execute_workflow_action_log_audit():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.event_workflow.boto3.client", return_value=mock_client):
        result = execute_workflow_action(
            "log_audit",
            {"event_type": "anomaly_detected", "ticker": "AAPL"},
            "test-bucket",
        )
    assert isinstance(result, dict)
    assert result["action"] == "log_audit"
    assert result["success"] is True
    mock_client.put_object.assert_called_once()


def test_process_event_structure():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.event_workflow.boto3.client", return_value=mock_client):
        with patch("ingestion.event_workflow.slack_alerter.send_slack_message", return_value=True):
            result = process_event(
                "anomaly_detected",
                {"ticker": "AAPL", "anomaly_label": "SPIKE"},
                "test-bucket",
            )
    assert isinstance(result, dict)
    assert "triggers_fired" in result
    assert "actions_executed" in result
    assert "event_type" in result
    assert result["triggers_fired"] > 0


def test_save_workflow_log_success():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.event_workflow.boto3.client", return_value=mock_client):
        result = save_workflow_log(
            "anomaly_detected",
            {"triggers_fired": 1, "actions_executed": 3},
            "test-bucket",
        )
    assert result is True
    mock_client.put_object.assert_called_once()
