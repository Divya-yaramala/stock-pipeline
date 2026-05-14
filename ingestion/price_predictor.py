import pandas as pd
import numpy as np
from prophet import Prophet
import logging
import json
import os
import boto3
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def load_historical_data_from_s3(ticker: str, bucket: str, days: int = 30) -> pd.DataFrame:
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    frames = []
    today = datetime.now()

    for i in range(days):
        day = today - timedelta(days=i + 1)
        date_str = day.strftime("%Y/%m/%d")
        key = f"raw/stocks/{date_str}/{ticker}.json"
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            data = json.loads(response["Body"].read().decode("utf-8"))
            df = pd.DataFrame(data)
            df.columns = [col.lower() for col in df.columns]
            df.index = pd.to_datetime(df.index)
            df.index.name = "date"
            df = df.reset_index()
            frames.append(df)
        except Exception:
            continue

    if not frames:
        logger.warning(f"No historical data found for {ticker}")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Loaded {len(frames)} days of data for {ticker} ({len(combined)} rows)")
    return combined


def prepare_prophet_data(df: pd.DataFrame) -> pd.DataFrame:
    prophet_df = df[["date", "close"]].copy()
    prophet_df = prophet_df.rename(columns={"date": "ds", "close": "y"})
    prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])
    prophet_df = prophet_df.dropna()
    return prophet_df.reset_index(drop=True)


def train_and_predict(df: pd.DataFrame, ticker: str, forecast_days: int = 5) -> pd.DataFrame:
    model = Prophet(daily_seasonality=True)
    model.fit(df)
    future = model.make_future_dataframe(periods=forecast_days)
    forecast = model.predict(future)
    result = (
        forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]
        .tail(forecast_days)
        .reset_index(drop=True)
    )
    for _, row in result.iterrows():
        logger.info(f"{ticker} predicted close on {row['ds'].date()}: ${row['yhat']:.2f}")
    return result


def save_predictions_to_s3(df: pd.DataFrame, ticker: str, bucket: str, date: str) -> bool:
    try:
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        key = f"processed/predictions/{date}/{ticker}.json"
        json_str = df.to_json(date_format="iso")
        s3_client.put_object(Bucket=bucket, Key=key, Body=json_str)
        logger.info(f"Saved predictions to s3://{bucket}/{key}")
        return True
    except Exception as e:
        logger.error(f"Failed to save predictions for {ticker}: {e}")
        return False


def run_price_prediction() -> None:
    date = datetime.now().strftime("%Y/%m/%d")
    succeeded = 0
    failed = 0
    for ticker in TICKERS:
        try:
            df = load_historical_data_from_s3(ticker, AWS_BUCKET_NAME)
            if df.empty:
                logger.warning(f"No data for {ticker}, skipping")
                failed += 1
                continue
            prophet_df = prepare_prophet_data(df)
            forecast = train_and_predict(prophet_df, ticker)
            if save_predictions_to_s3(forecast, ticker, AWS_BUCKET_NAME, date):
                succeeded += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Prediction error for {ticker}: {e}")
            failed += 1
    logger.info(
        f"Price prediction complete: {succeeded} tickers predicted successfully, {failed} failed"
    )


if __name__ == "__main__":
    run_price_prediction()
