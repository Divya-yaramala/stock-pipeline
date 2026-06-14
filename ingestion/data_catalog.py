import hashlib
import json
import logging
import os
from datetime import datetime, timezone

import boto3

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DATASETS = [
    {
        "name": "stock_prices_raw",
        "description": "Raw OHLCV data from Yahoo Finance for 5 tickers",
        "source": "Yahoo Finance via yfinance",
        "owner": "data-engineering",
        "schema": {
            "ticker": "VARCHAR(10)",
            "trade_date": "DATE",
            "open_price": "NUMERIC(12,4)",
            "high_price": "NUMERIC(12,4)",
            "low_price": "NUMERIC(12,4)",
            "close_price": "NUMERIC(12,4)",
            "volume": "BIGINT",
        },
    },
    {
        "name": "stock_anomalies",
        "description": "Isolation Forest anomaly detection results per ticker per day",
        "source": "ingestion/anomaly_detector.py",
        "owner": "ml-team",
        "schema": {
            "ticker": "VARCHAR(10)",
            "trade_date": "DATE",
            "is_anomaly": "BOOLEAN",
            "anomaly_score": "NUMERIC(10,6)",
        },
    },
    {
        "name": "stock_predictions",
        "description": "Prophet 5-day price forecasts with confidence bounds",
        "source": "ingestion/price_predictor.py",
        "owner": "ml-team",
        "schema": {
            "ticker": "VARCHAR(10)",
            "prediction_date": "DATE",
            "predicted_close": "NUMERIC(12,4)",
            "lower_bound": "NUMERIC(12,4)",
            "upper_bound": "NUMERIC(12,4)",
        },
    },
    {
        "name": "stock_insights",
        "description": "GPT-3.5 generated 3-sentence market insight summaries",
        "source": "ingestion/market_insights.py",
        "owner": "ai-team",
        "schema": {"ticker": "VARCHAR(10)", "insight_date": "DATE", "insight_text": "TEXT"},
    },
    {
        "name": "stock_sentiment",
        "description": "Keyword-based news sentiment scores (BULLISH/BEARISH/NEUTRAL)",
        "source": "ingestion/news_sentiment.py",
        "owner": "data-engineering",
        "schema": {
            "ticker": "VARCHAR(10)",
            "date": "DATE",
            "sentiment_label": "VARCHAR(10)",
            "sentiment_score": "NUMERIC(6,2)",
        },
    },
    {
        "name": "stock_technical",
        "description": "SMA, RSI, Bollinger Bands, and MACD technical indicators",
        "source": "ingestion/technical_indicators.py",
        "owner": "data-engineering",
        "schema": {
            "ticker": "VARCHAR(10)",
            "date": "DATE",
            "sma_20": "NUMERIC(12,4)",
            "rsi_14": "NUMERIC(6,2)",
            "macd": "NUMERIC(10,4)",
        },
    },
]


def register_dataset(
    dataset_name: str,
    description: str,
    schema: dict,
    source: str,
    owner: str,
    bucket: str,
) -> str:
    raw = f"{dataset_name}{datetime.now(timezone.utc).isoformat()}"
    dataset_id = hashlib.md5(raw.encode()).hexdigest()

    entry = {
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "description": description,
        "schema": schema,
        "source": source,
        "owner": owner,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "tags": [],
        "status": "active",
    }

    s3 = boto3.client("s3")
    key = f"catalog/datasets/{dataset_name}/metadata.json"
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(entry, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    logger.info("Dataset registered: %s (id=%s)", dataset_name, dataset_id)
    return dataset_id


def update_dataset_stats(
    dataset_name: str,
    row_count: int,
    last_updated: str,
    bucket: str,
) -> bool:
    s3 = boto3.client("s3")
    key = f"catalog/datasets/{dataset_name}/metadata.json"
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        entry = json.loads(response["Body"].read().decode("utf-8"))
        entry["row_count"] = row_count
        entry["last_updated"] = last_updated
        entry["stats_refreshed_at"] = datetime.now(timezone.utc).isoformat()
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(entry, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info(
            "Stats updated for %s: %d rows, last_updated=%s", dataset_name, row_count, last_updated
        )
        return True
    except Exception as e:
        logger.error("Failed to update stats for %s: %s", dataset_name, e)
        return False


def search_catalog(query: str, bucket: str) -> list:
    s3 = boto3.client("s3")
    results = []
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix="catalog/datasets/")
        for obj in response.get("Contents", []):
            if not obj["Key"].endswith("metadata.json"):
                continue
            try:
                data = s3.get_object(Bucket=bucket, Key=obj["Key"])
                entry = json.loads(data["Body"].read().decode("utf-8"))
                q = query.lower()
                if (
                    q in entry.get("dataset_name", "").lower()
                    or q in entry.get("description", "").lower()
                ):
                    results.append(entry)
            except Exception:
                pass
    except Exception as e:
        logger.error("Catalog search failed: %s", e)

    logger.info("Catalog search '%s': %d result(s) found", query, len(results))
    return results


def get_dataset_lineage(dataset_name: str, bucket: str) -> dict:
    s3 = boto3.client("s3")
    upstream: list = []
    downstream: list = []

    try:
        prefix = f"lineage/{dataset_name}/"
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        for obj in response.get("Contents", []):
            try:
                data = s3.get_object(Bucket=bucket, Key=obj["Key"])
                record = json.loads(data["Body"].read().decode("utf-8"))
                upstream.extend(record.get("upstream", []))
                downstream.extend(record.get("downstream", []))
            except Exception:
                pass
    except Exception as e:
        logger.warning("Could not load lineage for %s: %s", dataset_name, e)

    return {"upstream": upstream, "downstream": downstream}


def run_catalog_registration() -> None:
    bucket = os.getenv("AWS_BUCKET_NAME", "")
    register_dataset(
        dataset_name="stock_prices_raw",
        description="Raw OHLCV data from Yahoo Finance for 5 tickers",
        schema={
            "ticker": "VARCHAR(10)",
            "trade_date": "DATE",
            "open_price": "NUMERIC(12,4)",
            "close_price": "NUMERIC(12,4)",
            "volume": "BIGINT",
        },
        source="Yahoo Finance via yfinance",
        owner="data-engineering",
        bucket=bucket,
    )
    register_dataset(
        dataset_name="stock_anomalies",
        description="Isolation Forest anomaly detection results per ticker per day",
        schema={
            "ticker": "VARCHAR(10)",
            "trade_date": "DATE",
            "is_anomaly": "BOOLEAN",
            "anomaly_score": "NUMERIC(10,6)",
        },
        source="ingestion/anomaly_detector.py",
        owner="ml-team",
        bucket=bucket,
    )
    register_dataset(
        dataset_name="stock_predictions",
        description="Prophet 5-day price forecasts with confidence bounds",
        schema={
            "ticker": "VARCHAR(10)",
            "prediction_date": "DATE",
            "predicted_close": "NUMERIC(12,4)",
            "lower_bound": "NUMERIC(12,4)",
            "upper_bound": "NUMERIC(12,4)",
        },
        source="ingestion/price_predictor.py",
        owner="ml-team",
        bucket=bucket,
    )
    register_dataset(
        dataset_name="stock_insights",
        description="GPT-3.5 generated 3-sentence market insight summaries",
        schema={"ticker": "VARCHAR(10)", "insight_date": "DATE", "insight_text": "TEXT"},
        source="ingestion/market_insights.py",
        owner="ai-team",
        bucket=bucket,
    )
    register_dataset(
        dataset_name="stock_sentiment",
        description="Keyword-based news sentiment scores (BULLISH/BEARISH/NEUTRAL)",
        schema={
            "ticker": "VARCHAR(10)",
            "date": "DATE",
            "sentiment_label": "VARCHAR(10)",
            "sentiment_score": "NUMERIC(6,2)",
        },
        source="ingestion/news_sentiment.py",
        owner="data-engineering",
        bucket=bucket,
    )
    register_dataset(
        dataset_name="stock_technical",
        description="SMA, RSI, Bollinger Bands, and MACD technical indicators",
        schema={
            "ticker": "VARCHAR(10)",
            "date": "DATE",
            "sma_20": "NUMERIC(12,4)",
            "rsi_14": "NUMERIC(6,2)",
            "macd": "NUMERIC(10,4)",
        },
        source="ingestion/technical_indicators.py",
        owner="data-engineering",
        bucket=bucket,
    )
    logger.info("Catalog registration complete")


if __name__ == "__main__":
    run_catalog_registration()
