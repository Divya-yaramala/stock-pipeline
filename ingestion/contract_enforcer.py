import datetime
import json
import logging
from typing import Any, Dict, List

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_CONTRACT_SCHEMA: Dict[str, Any] = {
    "contract_id": "C001",
    "name": "stock_price_event",
    "required_fields": [
        "ticker",
        "trade_date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
    ],
    "field_types": {
        "ticker": "str",
        "trade_date": "str",
        "open_price": "float",
        "high_price": "float",
        "low_price": "float",
        "close_price": "float",
        "volume": "int",
    },
}


def enforce_contract(data: Dict[str, Any], contract_id: str, bucket: str) -> Dict[str, Any]:
    violations: List[str] = []
    try:
        s3 = boto3.client("s3")
        key = f"data_contracts/{contract_id}.json"
        resp = s3.get_object(Bucket=bucket, Key=key)
        contract: Dict[str, Any] = json.loads(resp["Body"].read().decode())
    except Exception:
        contract = _CONTRACT_SCHEMA

    required_fields: List[str] = contract.get("required_fields", [])
    for field in required_fields:
        if field not in data:
            violations.append(f"Missing required field: {field}")
        elif data[field] is None:
            violations.append(f"Null value in required field: {field}")

    blocked = len(violations) > 0
    result: Dict[str, Any] = {
        "enforced": True,
        "violations": violations,
        "contract_id": contract_id,
        "blocked": blocked,
    }
    logger.info(
        "Contract %s enforcement: blocked=%s violations=%d",
        contract_id,
        blocked,
        len(violations),
    )
    return result


def log_contract_violation(
    contract_id: str, violations: List[str], ticker: str, bucket: str
) -> bool:
    try:
        s3 = boto3.client("s3")
        now = datetime.datetime.utcnow()
        key = (
            f"contracts/violations/{now.year}/{now.month:02d}/{now.day:02d}/"
            f"{contract_id}_{ticker}.json"
        )
        payload: Dict[str, Any] = {
            "contract_id": contract_id,
            "ticker": ticker,
            "violations": violations,
            "timestamp": now.isoformat(),
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload).encode())
        logger.info("Violation recorded: s3://%s/%s", bucket, key)
        return True
    except Exception as e:
        logger.error("Failed to log violation: %s", e)
        return False


def get_contract_violation_history(
    contract_id: str, bucket: str, days: int = 7
) -> List[Dict[str, Any]]:
    violations: List[Dict[str, Any]] = []
    try:
        s3 = boto3.client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        for i in range(days):
            d = datetime.datetime.utcnow() - datetime.timedelta(days=i)
            prefix = f"contracts/violations/{d.year}/{d.month:02d}/{d.day:02d}/{contract_id}_"
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    try:
                        resp = s3.get_object(Bucket=bucket, Key=str(obj["Key"]))
                        violations.append(json.loads(resp["Body"].read().decode()))
                    except Exception:
                        continue
    except Exception as e:
        logger.error("Failed to load violation history: %s", e)
    logger.info("Found %d violations for contract %s", len(violations), contract_id)
    return violations


def calculate_contract_health(contract_id: str, bucket: str, days: int = 7) -> Dict[str, Any]:
    violations = get_contract_violation_history(contract_id, bucket, days)
    total_checks = days
    violation_count = len(violations)
    violation_rate = (violation_count / total_checks * 100) if total_checks > 0 else 0.0
    health_score = max(0.0, 100.0 - violation_rate)
    result: Dict[str, Any] = {
        "contract_id": contract_id,
        "health_score": round(health_score, 1),
        "violation_rate_pct": round(violation_rate, 1),
    }
    logger.info(
        "Contract %s health: %.1f (violation_rate=%.1f%%)",
        contract_id,
        health_score,
        violation_rate,
    )
    return result


def run_contract_enforcement(ticker: str, data: Dict[str, Any], bucket: str) -> Dict[str, Any]:
    result = enforce_contract(data, "C001", bucket)
    if result["blocked"]:
        log_contract_violation("C001", result["violations"], ticker, bucket)
    logger.info("Contract Enforcement Complete for %s", ticker)
    return result


if __name__ == "__main__":
    pass
