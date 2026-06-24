import boto3
import json
import os
import logging
import datetime
import random
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHAOS_SCENARIOS = [
    {"scenario_id": "C001", "name": "s3_latency", "description": "Simulate S3 high latency", "probability": 0.1},
    {"scenario_id": "C002", "name": "api_timeout", "description": "Simulate API timeout", "probability": 0.1},
    {"scenario_id": "C003", "name": "data_corruption", "description": "Simulate corrupted data", "probability": 0.05},
    {"scenario_id": "C004", "name": "partial_failure", "description": "Simulate partial ticker failure", "probability": 0.15},
    {"scenario_id": "C005", "name": "network_partition", "description": "Simulate network issues", "probability": 0.05},
]


def should_inject_chaos(scenario_id: str) -> bool:
    if os.environ.get("CHAOS_ENABLED", "").lower() != "true":
        return False
    scenario = next((s for s in CHAOS_SCENARIOS if s["scenario_id"] == scenario_id), None)
    if not scenario:
        return False
    result = random.random() < scenario["probability"]
    if result:
        logger.info(f"Chaos injected: {scenario['name']} ({scenario_id})")
    return result


def inject_latency(seconds: float = 2.0) -> None:
    logger.info(f"Injecting latency of {seconds}s")
    time.sleep(seconds)


def inject_data_corruption(data: dict) -> dict:
    if not data:
        return data
    corrupted = data.copy()
    field = random.choice(list(corrupted.keys()))
    corrupted[field] = None if random.random() < 0.5 else -abs(random.uniform(1, 100))
    logger.info(f"Data corruption injected: field '{field}' corrupted")
    return corrupted


def inject_partial_failure(tickers: list) -> list:
    if len(tickers) <= 1:
        return tickers
    num_to_remove = random.randint(1, min(2, len(tickers) - 1))
    failed = random.sample(tickers, num_to_remove)
    remaining = [t for t in tickers if t not in failed]
    logger.info(f"Partial failure injected: tickers {failed} removed")
    return remaining


def run_chaos_report(bucket: str, date: str) -> dict:
    s3 = boto3.client("s3")
    try:
        dt = datetime.datetime.strptime(date, "%Y-%m-%d")
        prefix = f"chaos/{dt.year:04d}/{dt.month:02d}/{dt.day:02d}/"
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        objects = response.get("Contents", [])
        by_scenario = {}
        for obj in objects:
            try:
                body = s3.get_object(Bucket=bucket, Key=obj["Key"])["Body"].read()
                event = json.loads(body)
                sid = event.get("scenario_id", "unknown")
                by_scenario[sid] = by_scenario.get(sid, 0) + 1
            except Exception:
                pass
        return {"total_events": len(objects), "by_scenario": by_scenario}
    except Exception as e:
        logger.error(f"Failed to run chaos report: {e}")
        return {"total_events": 0, "by_scenario": {}}


def save_chaos_event(scenario_id: str, details: dict, bucket: str) -> bool:
    s3 = boto3.client("s3")
    now = datetime.datetime.utcnow()
    timestamp = now.strftime("%H%M%S%f")
    key = f"chaos/{now.year:04d}/{now.month:02d}/{now.day:02d}/{scenario_id}_{timestamp}.json"
    event = {
        "scenario_id": scenario_id,
        "timestamp": now.isoformat(),
        "details": details,
    }
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(event))
        logger.info(f"Chaos event saved: {key}")
        return True
    except Exception as e:
        logger.error(f"Failed to save chaos event: {e}")
        return False


if __name__ == "__main__":
    pass
