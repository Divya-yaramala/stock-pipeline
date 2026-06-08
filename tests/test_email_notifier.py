import os
from unittest.mock import MagicMock, patch

from ingestion.email_notifier import send_alert_email, send_daily_report_email, send_email

_SMTP_ENV = {
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": "587",
    "SMTP_USER": "user@gmail.com",
    "SMTP_PASSWORD": "app-password",
}


def test_send_email_success():
    with patch.dict(os.environ, _SMTP_ENV):
        with patch("ingestion.email_notifier.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = send_email("to@example.com", "Test Subject", "<p>body</p>")
    assert result is True


def test_send_email_failure():
    with patch.dict(os.environ, _SMTP_ENV):
        with patch("ingestion.email_notifier.smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.side_effect = Exception("Connection refused")
            result = send_email("to@example.com", "Test Subject", "<p>body</p>")
    assert result is False


def test_send_email_no_credentials():
    with patch.dict(os.environ, {"SMTP_HOST": "", "SMTP_USER": "", "SMTP_PASSWORD": ""}):
        result = send_email("to@example.com", "Test Subject", "<p>body</p>")
    assert result is False


def test_send_daily_report_email_success():
    with patch("ingestion.email_notifier.send_email", return_value=True) as mock_send:
        result = send_daily_report_email("<html>report</html>", "2026-06-08")
    assert result is True
    mock_send.assert_called_once()


def test_send_alert_email_correct_subject():
    with patch("ingestion.email_notifier.send_email", return_value=True) as mock_send:
        result = send_alert_email("SLA_MISS", "Step exceeded threshold", "AAPL")
    assert result is True
    subject = mock_send.call_args.args[1]
    assert "SLA_MISS" in subject
