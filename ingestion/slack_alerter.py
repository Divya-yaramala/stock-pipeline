import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")


def send_slack_message(
    message: str,
    color: str = "good",
    title: Optional[str] = None,
    fields: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not set — skipping Slack notification")
        return False
    attachment: Dict[str, Any] = {"color": color, "text": message}
    if title:
        attachment["title"] = title
    if fields:
        attachment["fields"] = fields
    payload = {"attachments": [attachment]}
    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        if response.status_code == 200:
            logger.info("Slack message sent: %s", title or message[:60])
            return True
        logger.error("Slack returned status %d", response.status_code)
        return False
    except Exception as e:
        logger.error("Failed to send Slack message: %s", e)
        return False


def alert_anomaly_detected(
    ticker: str,
    anomaly_label: str,
    price: float,
    anomaly_score: float,
    date: str,
) -> bool:
    fields: List[Dict[str, Any]] = [
        {"title": "Label", "value": str(anomaly_label), "short": True},
        {"title": "Price", "value": f"${float(str(price)):.2f}", "short": True},
        {"title": "Score", "value": str(round(float(str(anomaly_score)), 4)), "short": True},
        {"title": "Date", "value": str(date), "short": True},
    ]
    return send_slack_message(
        message=f"Anomaly detected for {ticker} on {date}",
        color="danger",
        title=f"🚨 Anomaly Detected: {ticker}",
        fields=fields,
    )


def alert_prediction_ready(
    ticker: str,
    predicted_price: float,
    confidence: str,
    forecast_date: str,
) -> bool:
    fields: List[Dict[str, Any]] = [
        {"title": "Predicted Price", "value": f"${float(str(predicted_price)):.2f}", "short": True},
        {"title": "Confidence", "value": str(confidence), "short": True},
        {"title": "Forecast Date", "value": str(forecast_date), "short": True},
    ]
    return send_slack_message(
        message=f"5-day forecast available for {ticker}",
        color="good",
        title=f"📈 Prediction Ready: {ticker}",
        fields=fields,
    )


def alert_pipeline_failure(
    step: str,
    error: str,
    ticker: Optional[str] = None,
) -> bool:
    ticker_str = f" [{ticker}]" if ticker else ""
    fields: List[Dict[str, Any]] = [
        {"title": "Step", "value": str(step), "short": True},
        {"title": "Error", "value": str(error), "short": False},
    ]
    if ticker:
        fields.insert(0, {"title": "Ticker", "value": str(ticker), "short": True})
    return send_slack_message(
        message=f"Pipeline failure in step '{step}'{ticker_str}: {error}",
        color="danger",
        title=f"❌ Pipeline Failure: {step}",
        fields=fields,
    )


def alert_quality_warning(
    ticker: str,
    quality_score: float,
    issues: List[str],
) -> bool:
    issues_str = ", ".join(issues) if issues else "none"
    fields: List[Dict[str, Any]] = [
        {"title": "Quality Score", "value": f"{float(str(quality_score)):.1f}%", "short": True},
        {"title": "Issues", "value": str(issues_str), "short": False},
    ]
    return send_slack_message(
        message=f"Quality score {float(str(quality_score)):.1f}% is below threshold for {ticker}",
        color="warning",
        title=f"⚠️ Quality Warning: {ticker}",
        fields=fields,
    )


def send_daily_summary(
    total_tickers: int,
    anomalies_found: int,
    predictions_made: int,
    avg_quality_score: float,
) -> bool:
    fields: List[Dict[str, Any]] = [
        {"title": "Tickers Processed", "value": str(int(str(total_tickers))), "short": True},
        {"title": "Anomalies Found", "value": str(int(str(anomalies_found))), "short": True},
        {"title": "Predictions Made", "value": str(int(str(predictions_made))), "short": True},
        {
            "title": "Avg Quality Score",
            "value": f"{float(str(avg_quality_score)):.1f}%",
            "short": True,
        },
    ]
    avg_q = float(str(avg_quality_score))
    msg = (
        f"Pipeline completed: {total_tickers} tickers, "
        f"{anomalies_found} anomalies, avg quality {avg_q:.1f}%"
    )
    return send_slack_message(
        message=msg,
        color="good",
        title="📊 Daily Pipeline Summary",
        fields=fields,
    )


def alert_pipeline_success(step: str, ticker: str, duration: float) -> bool:
    message = f"✅ {step} {ticker} completed in {float(str(duration)):.1f}s"
    return send_slack_message(message, color="good")


if __name__ == "__main__":
    pass
