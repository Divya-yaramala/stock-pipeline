import json
import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
REPORT_EMAIL_TO = os.getenv("REPORT_EMAIL_TO", "")


def send_email(to: str, subject: str, html_body: str) -> bool:
    """
    Send an HTML email via SMTP.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        html_body: HTML content for the email body.

    Returns:
        True on success, False on failure or missing credentials.
    """
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")

    if not all([host, user, password, to]):
        logger.warning("SMTP credentials not fully configured — email not sent to %s", to)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)

        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


def send_daily_report_email(report_html: str, date: str) -> bool:
    """
    Send the daily HTML pipeline report via email.

    Args:
        report_html: Rendered HTML report string.
        date: Date string in YYYY-MM-DD format, used in the subject line.

    Returns:
        True on success, False on failure.
    """
    to = os.getenv("REPORT_EMAIL_TO", "")
    subject = f"Daily Pipeline Report - {date}"
    return send_email(to, subject, report_html)


def send_alert_email(alert_type: str, message: str, ticker: str) -> bool:
    """
    Send an alert email for a critical pipeline failure.

    Args:
        alert_type: Short label for the alert (e.g., "SLA_MISS", "DATA_QUALITY").
        message: Human-readable description of the failure.
        ticker: Stock ticker associated with the alert.

    Returns:
        True on success, False on failure.
    """
    to = os.getenv("REPORT_EMAIL_TO", "")
    subject = f"ALERT: stock_price_pipeline - {alert_type}"
    timestamp = datetime.utcnow().isoformat()
    detail = json.dumps(
        {"ticker": ticker, "alert_type": alert_type, "message": message, "timestamp": timestamp},
        indent=2,
    )
    html_body = f"""
    <h2>ALERT: {alert_type}</h2>
    <p><b>Ticker:</b> {ticker}</p>
    <p><b>Message:</b> {message}</p>
    <p><b>Time:</b> {timestamp}</p>
    <pre>{detail}</pre>
    """
    return send_email(to, subject, html_body)


if __name__ == "__main__":
    _bucket = os.getenv("AWS_BUCKET_NAME", "")
    _s3 = boto3.client("s3")
    logger.info("Email notifier ready. Recipient: %s", REPORT_EMAIL_TO)
