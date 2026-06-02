import json
import logging
import os
from datetime import datetime

import boto3
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from ingestion.config_manager import load_aws_config, load_pipeline_config

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def load_todays_data(ticker: str, bucket: str, date: str) -> dict:
    """
    Load raw, anomaly, and prediction data for a ticker from S3.

    Args:
        ticker: Stock ticker symbol.
        bucket: S3 bucket name.
        date: Date string in YYYY/MM/DD format.

    Returns:
        Dict with keys 'raw', 'anomalies', 'predictions'; values are dicts or None
        if a given S3 object was not found.
    """
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    result = {"raw": None, "anomalies": None, "predictions": None}

    paths = {
        "raw": f"raw/stocks/{date}/{ticker}.json",
        "anomalies": f"processed/anomalies/{date}/{ticker}.json",
        "predictions": f"processed/predictions/{date}/{ticker}.json",
    }

    for key, s3_key in paths.items():
        try:
            response = s3_client.get_object(Bucket=bucket, Key=s3_key)
            result[key] = json.loads(response["Body"].read().decode("utf-8"))
        except Exception as e:
            logger.warning(
                f"Could not load {key} data for {ticker} from s3://{bucket}/{s3_key}: {e}"
            )

    return result


def build_prompt(ticker: str, data: dict) -> str:
    """
    Build a GPT market-insight prompt from today's OHLCV, anomaly flag, and forecasts.

    Args:
        ticker: Stock ticker symbol.
        data: Dict returned by load_todays_data.

    Returns:
        Formatted prompt string ready to send to OpenAI.
    """
    raw = data.get("raw") or {}
    open_val = next(iter((raw.get("Open") or raw.get("open") or {}).values()), "N/A")
    high_val = next(iter((raw.get("High") or raw.get("high") or {}).values()), "N/A")
    low_val = next(iter((raw.get("Low") or raw.get("low") or {}).values()), "N/A")
    close_val = next(iter((raw.get("Close") or raw.get("close") or {}).values()), "N/A")
    volume_val = next(iter((raw.get("Volume") or raw.get("volume") or {}).values()), "N/A")

    anomalies = data.get("anomalies") or {}
    is_anomaly_col = anomalies.get("is_anomaly") or {}
    anomaly_detected = any(v for v in is_anomaly_col.values()) if is_anomaly_col else False

    predictions = data.get("predictions") or {}
    yhat_col = predictions.get("yhat") or {}
    ds_col = predictions.get("ds") or {}
    predicted = [
        f"{ds_col.get(str(i), 'Day ' + str(i + 1))}: ${yhat_col.get(str(i), 0.0):.2f}"
        for i in range(len(yhat_col))
    ]
    predicted_str = ", ".join(predicted) if predicted else "N/A"

    prompt = (
        f"You are a professional financial analyst. Write a 3-sentence market insight summary "
        f"for {ticker} based on the following data. "
        f"Keep the language professional and data-driven.\n\n"
        f"Today's OHLCV data for {ticker}:\n"
        f"  Open: {open_val}, High: {high_val}, Low: {low_val}, "
        f"Close: {close_val}, Volume: {volume_val}\n\n"
        f"Anomaly detected today: {anomaly_detected}\n\n"
        f"Next 5 days predicted closing prices: {predicted_str}\n\n"
        f"Write exactly 3 sentences summarizing the market outlook for {ticker}."
    )
    return prompt


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def generate_insight(prompt: str, ticker: str) -> str:
    """
    Send a prompt to OpenAI and return the generated insight text.

    Retries up to 3 times with exponential backoff (2s → 4s → 8s capped at 30s).
    Rate limit errors are logged as warnings and re-raised for tenacity to retry;
    other API errors are logged as errors before re-raising.

    Args:
        prompt: Formatted market insight prompt.
        ticker: Stock ticker symbol (used for logging).

    Returns:
        Generated insight string, or empty string on failure.
    """
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        insight = response.choices[0].message.content or ""
        logger.info(f"{ticker} insight: {insight[:100]}")
        return insight
    except openai.RateLimitError as e:
        logger.warning(f"OpenAI rate limit hit for {ticker}, will retry: {e}")
        raise
    except Exception as e:
        logger.error(f"OpenAI API error for {ticker}: {e}")
        raise


def save_insight_to_s3(insight: str, ticker: str, bucket: str, date: str) -> bool:
    """
    Serialize insight to JSON and upload to S3.

    Args:
        insight: Generated insight text.
        ticker: Stock ticker symbol.
        bucket: S3 bucket name.
        date: Date string in YYYY/MM/DD format.

    Returns:
        True on success, False on failure.
    """
    try:
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        key = f"processed/insights/{date}/{ticker}.json"
        payload = json.dumps({"ticker": ticker, "date": date, "insight": insight})
        s3_client.put_object(Bucket=bucket, Key=key, Body=payload)
        logger.info(f"Saved insight to s3://{bucket}/{key}")
        return True
    except Exception as e:
        logger.error(f"Failed to save insight for {ticker}: {e}")
        return False


def run_market_insights() -> None:
    """
    Generate AI market insights for all configured tickers and upload each to S3.

    Loads the ticker list from config_manager. For each ticker, loads today's data,
    builds a GPT prompt, generates an insight, saves it to S3, and records lineage.
    Failed tickers are sent to the dead-letter queue.
    """
    try:
        aws_cfg = load_aws_config()
        bucket = aws_cfg.bucket_name
    except ValueError:
        bucket = AWS_BUCKET_NAME

    pipeline_cfg = load_pipeline_config()
    tickers = pipeline_cfg.tickers

    date = datetime.now().strftime("%Y/%m/%d")
    succeeded = 0
    for ticker in tickers:
        try:
            data = load_todays_data(ticker, bucket, date)
            prompt = build_prompt(ticker, data)
            insight = generate_insight(prompt, ticker)
            if insight and save_insight_to_s3(insight, ticker, bucket, date):
                succeeded += 1
                from ingestion import lineage_tracker

                lineage_tracker.record_lineage(
                    source="s3_processed",
                    destination="s3_insights",
                    ticker=ticker,
                    row_count=1,
                    transformation="gpt_summarization",
                    bucket=bucket,
                )
        except Exception as e:
            logger.error(f"Market insights error for {ticker}: {e}")
            from ingestion import dead_letter_queue

            dead_letter_queue.send_to_dlq(str(e), ticker, "insights", {}, bucket)
    logger.info(f"Market insights complete: {succeeded} insights generated successfully")


if __name__ == "__main__":
    run_market_insights()
