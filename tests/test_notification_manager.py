import json
from unittest.mock import MagicMock, patch

from ingestion.notification_manager import (
    get_notification_history,
    run_notification_check,
    send_critical_alert,
    send_info_notification,
    send_notification,
)


def _make_s3_body(data: dict) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return body


def test_send_notification_structure():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.notification_manager.boto3.client", return_value=mock_client):
        with patch(
            "ingestion.notification_manager.slack_alerter.send_slack_message", return_value=True
        ):
            result = send_notification(
                title="Test Alert",
                message="Test message",
                severity="HIGH",
                channels=["slack", "s3_log"],
                bucket="test-bucket",
            )
    assert isinstance(result, dict)
    assert "sent" in result
    assert "failed" in result
    assert isinstance(result["sent"], list)


def test_send_critical_alert_success():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.notification_manager.boto3.client", return_value=mock_client):
        with patch(
            "ingestion.notification_manager.slack_alerter.send_slack_message", return_value=True
        ):
            with patch("ingestion.notification_manager._send_to_email", return_value=True):
                result = send_critical_alert(
                    title="Critical Alert",
                    message="Quality gate blocked",
                    ticker="AAPL",
                    bucket="test-bucket",
                )
    assert result is True


def test_send_info_notification_success():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.notification_manager.boto3.client", return_value=mock_client):
        result = send_info_notification(
            title="Info",
            message="Pipeline completed",
            bucket="test-bucket",
        )
    assert result is True


def test_get_notification_history_structure():
    record = {
        "title": "Test",
        "message": "msg",
        "severity": "HIGH",
        "logged_at": "2026-07-26T00:00:00",
    }
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [{"Key": "notifications/logs/2026/07/26/HIGH_20260726T000000.json"}]
    }
    mock_client.get_object.return_value = {"Body": _make_s3_body(record)}
    with patch("ingestion.notification_manager.boto3.client", return_value=mock_client):
        result = get_notification_history("test-bucket", "2026/07/26")
    assert isinstance(result, list)
    assert len(result) == 1


def test_run_notification_check_structure():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.notification_manager.boto3.client", return_value=mock_client):
        with patch(
            "ingestion.notification_manager.slack_alerter.send_slack_message", return_value=True
        ):
            with patch("ingestion.notification_manager._send_to_email", return_value=False):
                result = run_notification_check("test-bucket")
    assert isinstance(result, dict)
    assert "channels_tested" in result
    assert "working" in result
    assert "failed" in result
    assert result["channels_tested"] == 3
