import json
import logging
import os
from datetime import datetime

import boto3
import openai

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def load_todays_data(ticker: str, bucket: str, date: str) -> dict:
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


def generate_insight(prompt: str, ticker: str) -> str:
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
    except Exception as e:
        logger.error(f"OpenAI API error for {ticker}: {e}")
        return ""


def save_insight_to_s3(insight: str, ticker: str, bucket: str, date: str) -> bool:
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
    date = datetime.now().strftime("%Y/%m/%d")
    succeeded = 0
    for ticker in TICKERS:
        data = load_todays_data(ticker, AWS_BUCKET_NAME, date)
        prompt = build_prompt(ticker, data)
        insight = generate_insight(prompt, ticker)
        if insight and save_insight_to_s3(insight, ticker, AWS_BUCKET_NAME, date):
            succeeded += 1
    logger.info(f"Market insights complete: {succeeded} insights generated successfully")


if __name__ == "__main__":
    run_market_insights()
