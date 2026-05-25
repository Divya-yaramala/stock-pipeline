import json
import logging
import os

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")


def send_slack_message(message: str, color: str = "good") -> bool:
    """Send a message to Slack via webhook using the attachment format."""
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not set — skipping Slack notification")
        return False
    try:
        payload = {"attachments": [{"color": color, "text": message}]}
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        if response.status_code == 200:
            logger.info("Slack message sent: %s", message)
            return True
        logger.error("Slack returned status %d", response.status_code)
        return False
    except Exception as e:
        logger.error("Failed to send Slack message: %s", e)
        return False


def alert_pipeline_success(step: str, ticker: str, duration: float) -> bool:
    """Send a green success alert for a completed pipeline step."""
    message = f"✅ {step} {ticker} completed in {duration:.1f}s"
    return send_slack_message(message, color="good")


def alert_pipeline_failure(step: str, ticker: str, error: str) -> bool:
    """Send a red failure alert for a failed pipeline step."""
    message = f"❌ {step} {ticker} FAILED: {error}"
    return send_slack_message(message, color="danger")


def alert_daily_summary(report: dict) -> bool:
    """Send a daily pipeline summary to Slack with colour based on success rate."""
    rate = report.get("success_rate_pct", 0)
    color = "good" if rate >= 80 else ("warning" if rate >= 50 else "danger")
    message = (
        f"📊 Daily Pipeline Summary\n"
        f"Total runs: {report.get('total_runs', 0)} | "
        f"Success rate: {rate:.1f}% | "
        f"Slowest step: {report.get('slowest_step', 'N/A')}"
    )
    return send_slack_message(message, color=color)
