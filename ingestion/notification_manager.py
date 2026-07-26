import datetime
import json
import logging
import os
import smtplib
from typing import Any, Dict, List, Optional

import boto3
import requests

from ingestion import slack_alerter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

NOTIFICATION_CHANNELS: List[Dict[str, Any]] = [
    {"channel_id": "N001", "name": "slack", "enabled_flag": "enable_slack_alerts"},
    {"channel_id": "N002", "name": "email", "enabled_flag": "enable_email_reports"},
    {"channel_id": "N003", "name": "s3_log", "enabled_flag": None},
]


def _send_to_slack(title: str, message: str, severity: str) -> bool:
    color_map = {"CRITICAL": "danger", "HIGH": "danger", "MEDIUM": "warning", "LOW": "good", "INFO": "good"}
    color = color_map.get(severity.upper(), "warning")
    return slack_alerter.send_slack_message(message=message, title=title, color=color)


def _send_to_email(title: str, message: str, severity: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    email_to = os.getenv("REPORT_EMAIL_TO", "")

    if not all([smtp_host, smtp_user, smtp_password, email_to]):
        logger.warning("Email credentials not configured — skipping email notification")
        return False

    try:
        import email.mime.multipart
        import email.mime.text

        msg = email.mime.multipart.MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = email_to
        msg["Subject"] = f"[{severity}] {title}"
        msg.attach(email.mime.text.MIMEText(f"<h2>{title}</h2><p>{message}</p>", "html"))
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, email_to, msg.as_string())
        logger.info(f"Email sent: {title}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def _send_to_s3_log(
    title: str,
    message: str,
    severity: str,
    bucket: str,
) -> bool:
    try:
        s3 = boto3.client("s3")
        now = datetime.datetime.utcnow()
        date_path = now.strftime("%Y/%m/%d")
        timestamp = now.strftime("%Y%m%dT%H%M%S")
        key = f"notifications/logs/{date_path}/{severity}_{timestamp}.json"
        record = {
            "title": title,
            "message": message,
            "severity": severity,
            "logged_at": now.isoformat(),
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(record))
        logger.info(f"Notification log saved: {key}")
        return True
    except Exception as e:
        logger.error(f"Failed to save notification log: {e}")
        return False


def send_notification(
    title: str,
    message: str,
    severity: str,
    channels: Optional[List[str]] = None,
    bucket: str = "",
) -> Dict[str, Any]:
    if channels is None:
        channels = ["slack", "s3_log"]

    sent: List[str] = []
    failed: List[str] = []

    for channel in channels:
        try:
            if channel == "slack":
                ok = _send_to_slack(title, message, severity)
            elif channel == "email":
                ok = _send_to_email(title, message, severity)
            elif channel == "s3_log":
                ok = _send_to_s3_log(title, message, severity, bucket)
            else:
                ok = False

            if ok:
                sent.append(channel)
            else:
                failed.append(channel)
        except Exception as e:
            logger.error(f"Channel {channel} error: {e}")
            failed.append(channel)

    logger.info(f"Notification sent to channels: {sent} | failed: {failed}")
    return {"sent": sent, "failed": failed}


def send_critical_alert(
    title: str,
    message: str,
    ticker: Optional[str] = None,
    bucket: str = "",
) -> bool:
    full_title = f"{title}" + (f" [{ticker}]" if ticker else "")
    all_channels = [str(c["name"]) for c in NOTIFICATION_CHANNELS]
    result = send_notification(
        title=full_title,
        message=message,
        severity="CRITICAL",
        channels=all_channels,
        bucket=bucket,
    )
    success = len(result["sent"]) > 0
    logger.info(f"Critical alert sent: {full_title} | success={success}")
    return success


def send_info_notification(
    title: str,
    message: str,
    bucket: str = "",
) -> bool:
    result = send_notification(
        title=title,
        message=message,
        severity="INFO",
        channels=["s3_log"],
        bucket=bucket,
    )
    success = "s3_log" in result["sent"]
    return success


def get_notification_history(
    bucket: str,
    date: str,
    severity: Optional[str] = None,
) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3")
    prefix = f"notifications/logs/{date}/"
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    history: List[Dict[str, Any]] = []
    for obj in response.get("Contents", []):
        key = str(obj["Key"])
        resp = s3.get_object(Bucket=bucket, Key=key)
        record = json.loads(resp["Body"].read())
        if severity is None or str(record.get("severity", "")).upper() == severity.upper():
            history.append(record)
    logger.info(f"Found {len(history)} notifications for date: {date}")
    return history


def run_notification_check(bucket: str) -> Dict[str, Any]:
    channels_tested = len(NOTIFICATION_CHANNELS)
    working = 0
    failed_count = 0

    for channel in NOTIFICATION_CHANNELS:
        channel_name = str(channel["name"])
        try:
            if channel_name == "slack":
                ok = _send_to_slack("Health Check", "Notification system health check", "INFO")
            elif channel_name == "email":
                ok = _send_to_email("Health Check", "Notification system health check", "INFO")
            elif channel_name == "s3_log":
                ok = _send_to_s3_log("Health Check", "Notification system health check", "INFO", bucket)
            else:
                ok = False

            if ok:
                working += 1
            else:
                failed_count += 1
        except Exception as e:
            logger.error(f"Channel {channel_name} health check failed: {e}")
            failed_count += 1

    logger.info(f"Notification system health: {working}/{channels_tested} channels working")
    return {
        "channels_tested": channels_tested,
        "working": working,
        "failed": failed_count,
    }


if __name__ == "__main__":
    pass
