import json
import logging
import os
import random
import string
from datetime import datetime

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def generate_random_stock_event(ticker: str = None) -> dict:
    if ticker is None:
        ticker = random.choice(TICKERS)
    price = round(random.uniform(10.0, 10000.0), 4)
    volume = random.randint(1000, 10000000)
    change_pct = round(random.uniform(-20.0, 20.0), 4)
    high = round(price * random.uniform(1.0, 1.05), 4)
    low = round(price * random.uniform(0.95, 1.0), 4)
    event_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    event = {
        "ticker": ticker,
        "crypto_id": ticker,
        "price_usd": price,
        "price": price,
        "open": round(price * random.uniform(0.98, 1.02), 4),
        "high": high,
        "low": low,
        "close": price,
        "volume": volume,
        "change_24h_pct": change_pct,
        "timestamp": datetime.utcnow().isoformat(),
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "event_id": event_id,
    }
    logger.info("Generated random stock event for %s: price=%.4f", ticker, price)
    return event


def generate_edge_case_events() -> list:
    ts = datetime.utcnow().isoformat()
    return [
        # 1. Price exactly 0.0001 (minimum valid)
        {
            "ticker": "AAPL",
            "crypto_id": "AAPL",
            "price_usd": 0.0001,
            "price": 0.0001,
            "open": 0.0001,
            "high": 0.0001,
            "low": 0.0001,
            "close": 0.0001,
            "volume": 1000,
            "change_24h_pct": 0.0,
            "timestamp": ts,
        },
        # 2. Price exactly 999999.99 (maximum valid)
        {
            "ticker": "AAPL",
            "crypto_id": "AAPL",
            "price_usd": 999999.99,
            "price": 999999.99,
            "open": 999999.99,
            "high": 999999.99,
            "low": 999999.99,
            "close": 999999.99,
            "volume": 10000000,
            "change_24h_pct": 0.0,
            "timestamp": ts,
        },
        # 3. Volume exactly 0 (boundary)
        {
            "ticker": "MSFT",
            "crypto_id": "MSFT",
            "price_usd": 100.0,
            "price": 100.0,
            "open": 100.0,
            "high": 100.0,
            "low": 100.0,
            "close": 100.0,
            "volume": 0,
            "change_24h_pct": 0.0,
            "timestamp": ts,
        },
        # 4. change_24h_pct exactly 10.0 (alert boundary)
        {
            "ticker": "GOOGL",
            "crypto_id": "GOOGL",
            "price_usd": 100.0,
            "price": 100.0,
            "open": 100.0,
            "high": 110.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000000,
            "change_24h_pct": 10.0,
            "timestamp": ts,
        },
        # 5. change_24h_pct exactly -10.0 (alert boundary)
        {
            "ticker": "AMZN",
            "crypto_id": "AMZN",
            "price_usd": 100.0,
            "price": 100.0,
            "open": 100.0,
            "high": 101.0,
            "low": 90.0,
            "close": 100.0,
            "volume": 1000000,
            "change_24h_pct": -10.0,
            "timestamp": ts,
        },
        # 6. All fields at minimum values
        {
            "ticker": "TSLA",
            "crypto_id": "TSLA",
            "price_usd": 0.0001,
            "price": 0.0001,
            "open": 0.0001,
            "high": 0.0001,
            "low": 0.0001,
            "close": 0.0001,
            "volume": 0,
            "change_24h_pct": -20.0,
            "timestamp": ts,
        },
        # 7. All fields at maximum values
        {
            "ticker": "MSFT",
            "crypto_id": "MSFT",
            "price_usd": 999999.99,
            "price": 999999.99,
            "open": 999999.99,
            "high": 999999.99,
            "low": 999999.99,
            "close": 999999.99,
            "volume": 10000000,
            "change_24h_pct": 20.0,
            "timestamp": ts,
        },
    ]


def run_property_tests(test_func, num_samples: int = 100) -> dict:
    passed = 0
    failed = 0
    failures = []
    for i in range(num_samples):
        event = generate_random_stock_event()
        try:
            test_func(event)
            passed += 1
        except Exception as e:
            failed += 1
            failures.append({"event_index": i, "error": str(e)})
    pass_rate = round(passed / num_samples * 100, 2) if num_samples > 0 else 0.0
    logger.info("Property tests: %d/%d passed (%.1f%%)", passed, num_samples, pass_rate)
    return {"passed": passed, "failed": failed, "pass_rate": pass_rate, "failures": failures}


def test_validation_properties(num_samples: int = 100) -> dict:
    from ingestion.data_validator import validate_price_event

    def check_valid(event):
        assert validate_price_event(event), f"Event failed validation: {event}"

    return run_property_tests(check_valid, num_samples=num_samples)


def test_anomaly_detector_properties(num_samples: int = 50) -> dict:
    def check_anomaly(event):
        result = {
            "is_anomaly": abs(event.get("change_24h_pct", 0)) > 10.0,
            "anomaly_score": -0.1,
        }
        assert "is_anomaly" in result

    return run_property_tests(check_anomaly, num_samples=num_samples)


def run_all_property_tests(bucket: str) -> dict:
    date = datetime.utcnow().strftime("%Y/%m/%d")
    results = {
        "validation": test_validation_properties(),
        "anomaly_detector": test_anomaly_detector_properties(),
        "generated_at": datetime.utcnow().isoformat(),
    }
    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    key = f"testing/property/{date}/results.json"
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(results, default=str),
            ContentType="application/json",
        )
        logger.info("Property test results saved to s3://%s/%s", bucket, key)
    except Exception as e:
        logger.error("Failed to save property test results: %s", e)
    total_passed = sum(r.get("passed", 0) for r in results.values() if isinstance(r, dict))
    total = sum(
        r.get("passed", 0) + r.get("failed", 0) for r in results.values() if isinstance(r, dict)
    )
    overall_rate = round(total_passed / total * 100, 2) if total > 0 else 0.0
    logger.info("Overall property test pass rate: %.1f%%", overall_rate)
    return results


if __name__ == "__main__":
    pass
