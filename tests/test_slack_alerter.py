from unittest.mock import MagicMock, patch

from ingestion.slack_alerter import (
    alert_daily_summary,
    alert_pipeline_failure,
    alert_pipeline_success,
    send_slack_message,
)


def test_send_slack_message_success():
    with patch("ingestion.slack_alerter.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"):
        with patch("ingestion.slack_alerter.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_requests.post.return_value = mock_response
            result = send_slack_message("test message")
    assert result is True
    mock_requests.post.assert_called_once()


def test_send_slack_message_failure():
    with patch("ingestion.slack_alerter.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"):
        with patch("ingestion.slack_alerter.requests") as mock_requests:
            mock_requests.post.side_effect = Exception("network error")
            result = send_slack_message("test message")
    assert result is False


def test_send_slack_message_no_webhook():
    with patch("ingestion.slack_alerter.SLACK_WEBHOOK_URL", ""):
        result = send_slack_message("test message")
    assert result is False


def test_alert_pipeline_success_message():
    with patch("ingestion.slack_alerter.send_slack_message") as mock_send:
        mock_send.return_value = True
        alert_pipeline_success("fetch", "AAPL", 1.5)
    mock_send.assert_called_once()
    message = mock_send.call_args[0][0]
    assert "fetch" in message
    assert "AAPL" in message


def test_alert_pipeline_failure_message():
    with patch("ingestion.slack_alerter.send_slack_message") as mock_send:
        mock_send.return_value = True
        alert_pipeline_failure("anomaly", "MSFT", "connection timeout")
    mock_send.assert_called_once()
    message = mock_send.call_args[0][0]
    assert "connection timeout" in message


def test_alert_daily_summary_green():
    report = {
        "success_rate_pct": 100.0,
        "total_runs": 5,
        "successful_runs": 5,
        "failed_runs": 0,
        "slowest_step": "fetch",
    }
    with patch("ingestion.slack_alerter.send_slack_message") as mock_send:
        mock_send.return_value = True
        alert_daily_summary(report)
    mock_send.assert_called_once()
    color = mock_send.call_args[1].get("color") or mock_send.call_args[0][1]
    assert color == "good"
