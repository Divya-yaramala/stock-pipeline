import json
from unittest.mock import MagicMock, patch

from ingestion.slack_alerter import (
    alert_anomaly_detected,
    alert_quality_warning,
    send_daily_summary,
    send_slack_message,
)


def test_send_slack_message_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch("ingestion.slack_alerter.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"):
        with patch("ingestion.slack_alerter.requests.post", return_value=mock_response):
            result = send_slack_message("Test message", color="good")
    assert result is True


def test_send_slack_message_no_webhook():
    with patch("ingestion.slack_alerter.SLACK_WEBHOOK_URL", ""):
        result = send_slack_message("Test message")
    assert result is False


def test_send_slack_message_failure():
    with patch("ingestion.slack_alerter.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"):
        with patch("ingestion.slack_alerter.requests.post", side_effect=Exception("network error")):
            result = send_slack_message("Test message")
    assert result is False


def test_alert_anomaly_detected_message():
    with patch("ingestion.slack_alerter.send_slack_message", return_value=True) as mock_send:
        alert_anomaly_detected("AAPL", "SPIKE", 185.50, -0.42, "2024-01-15")
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["color"] == "danger"


def test_alert_quality_warning_color():
    with patch("ingestion.slack_alerter.send_slack_message", return_value=True) as mock_send:
        alert_quality_warning("AAPL", 72.0, ["missing_values", "outliers"])
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["color"] == "warning"


def test_send_daily_summary_color():
    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch("ingestion.slack_alerter.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"):
        with patch(
            "ingestion.slack_alerter.requests.post", return_value=mock_response
        ) as mock_post:
            send_daily_summary(5, 2, 5, 92.5)
            assert mock_post.called
            payload = json.loads(mock_post.call_args[1]["data"])
            assert payload["attachments"][0]["color"] == "good"
