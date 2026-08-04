import datetime
import hashlib
import json
import logging
from typing import Any, Dict, List

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LAKEHOUSE_LAYERS: List[Dict[str, Any]] = [
    {
        "layer_id": "L001",
        "name": "bronze",
        "description": "Raw ingested data",
        "s3_prefix": "lakehouse/bronze/",
        "retention_days": 365,
    },
    {
        "layer_id": "L002",
        "name": "silver",
        "description": "Cleaned and validated data",
        "s3_prefix": "lakehouse/silver/",
        "retention_days": 730,
    },
    {
        "layer_id": "L003",
        "name": "gold",
        "description": "Business-ready aggregations",
        "s3_prefix": "lakehouse/gold/",
        "retention_days": 1825,
    },
]

_REQUIRED_FIELDS: List[str] = [
    "ticker",
    "trade_date",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "volume",
]


def write_to_bronze(data: Dict[str, Any], ticker: str, source: str, bucket: str) -> str:
    try:
        s3 = boto3.client("s3")
        now = datetime.datetime.utcnow()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        record_id = hashlib.md5(f"{ticker}_{source}_{timestamp}".encode()).hexdigest()[:12]
        key = (
            f"lakehouse/bronze/{now.year}/{now.month:02d}/{now.day:02d}/"
            f"{ticker}/{source}_{timestamp}.json"
        )
        payload: Dict[str, Any] = {
            "record_id": record_id,
            "ticker": ticker,
            "source": source,
            "data": data,
            "ingested_at": now.isoformat(),
            "layer": "bronze",
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload).encode())
        logger.info("Bronze write: %s/%s (id=%s)", ticker, source, record_id)
        return record_id
    except Exception as e:
        logger.error("Bronze write failed: %s", e)
        return ""


def write_to_silver(data: Dict[str, Any], ticker: str, validation_score: float, bucket: str) -> str:
    if validation_score < 80.0:
        logger.info("Silver skipped: %s validation_score=%.1f < 80.0", ticker, validation_score)
        return ""
    try:
        s3 = boto3.client("s3")
        now = datetime.datetime.utcnow()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        record_id = hashlib.md5(f"{ticker}_silver_{timestamp}".encode()).hexdigest()[:12]
        key = (
            f"lakehouse/silver/{now.year}/{now.month:02d}/{now.day:02d}/"
            f"{ticker}/{record_id}.json"
        )
        payload: Dict[str, Any] = {
            "record_id": record_id,
            "ticker": ticker,
            "validation_score": validation_score,
            "data": data,
            "processed_at": now.isoformat(),
            "layer": "silver",
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload).encode())
        logger.info("Silver write: %s (score=%.1f id=%s)", ticker, validation_score, record_id)
        return record_id
    except Exception as e:
        logger.error("Silver write failed: %s", e)
        return ""


def write_to_gold(
    aggregation: Dict[str, Any], ticker: str, aggregation_type: str, bucket: str
) -> str:
    try:
        s3 = boto3.client("s3")
        now = datetime.datetime.utcnow()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        record_id = hashlib.md5(f"{ticker}_{aggregation_type}_{timestamp}".encode()).hexdigest()[
            :12
        ]
        key = (
            f"lakehouse/gold/{now.year}/{now.month:02d}/{now.day:02d}/"
            f"{ticker}/{aggregation_type}.json"
        )
        payload: Dict[str, Any] = {
            "record_id": record_id,
            "ticker": ticker,
            "aggregation_type": aggregation_type,
            "aggregation": aggregation,
            "created_at": now.isoformat(),
            "layer": "gold",
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload).encode())
        logger.info("Gold write: %s/%s (id=%s)", ticker, aggregation_type, record_id)
        return record_id
    except Exception as e:
        logger.error("Gold write failed: %s", e)
        return ""


def get_layer_stats(layer_name: str, bucket: str, date: str) -> Dict[str, Any]:
    try:
        s3 = boto3.client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        prefix = f"lakehouse/{layer_name}/{date}/"
        record_count = 0
        total_size = 0
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                record_count += 1
                total_size += int(str(obj.get("Size", 0)))
        size_mb = round(total_size / (1024 * 1024), 4)
        result: Dict[str, Any] = {
            "layer": layer_name,
            "record_count": record_count,
            "size_mb": size_mb,
        }
        logger.info(
            "Layer stats %s/%s: %d records %.4f MB",
            layer_name,
            date,
            record_count,
            size_mb,
        )
        return result
    except Exception as e:
        logger.error("Failed to get layer stats: %s", e)
        return {"layer": layer_name, "record_count": 0, "size_mb": 0.0}


def run_lakehouse_pipeline(ticker: str, raw_data: Dict[str, Any], bucket: str) -> Dict[str, Any]:
    bronze_id = write_to_bronze(raw_data, ticker, "yahoo_finance", bucket)

    present = sum(1 for f in _REQUIRED_FIELDS if f in raw_data and raw_data[f] is not None)
    validation_score = round((present / len(_REQUIRED_FIELDS)) * 100, 1)

    silver_id = write_to_silver(raw_data, ticker, validation_score, bucket)

    aggregation: Dict[str, Any] = {
        "avg_price": float(str(raw_data.get("close_price", 0))),
        "total_volume": int(str(raw_data.get("volume", 0))),
        "price_range": (
            float(str(raw_data.get("high_price", 0))) - float(str(raw_data.get("low_price", 0)))
        ),
        "date": str(raw_data.get("trade_date", "")),
    }
    gold_id = write_to_gold(aggregation, ticker, "daily_summary", bucket)

    result: Dict[str, Any] = {
        "bronze_id": bronze_id,
        "silver_id": silver_id,
        "gold_id": gold_id,
        "validation_score": validation_score,
    }
    logger.info("Lakehouse Pipeline Complete for %s", ticker)
    return result


if __name__ == "__main__":
    pass
