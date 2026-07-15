import datetime
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STOCK_PRICE_CONTRACT: Dict[str, Any] = {
    "contract_id": "C001",
    "name": "stock_price_event",
    "version": "1.0.0",
    "owner": "data_engineering",
    "schema": {
        "ticker": {"type": "string", "required": True, "pattern": "^[A-Z]{1,5}$"},
        "trade_date": {"type": "string", "required": True, "format": "YYYY-MM-DD"},
        "open_price": {"type": "float", "required": True, "min": 0},
        "high_price": {"type": "float", "required": True, "min": 0},
        "low_price": {"type": "float", "required": True, "min": 0},
        "close_price": {"type": "float", "required": True, "min": 0},
        "volume": {"type": "integer", "required": True, "min": 0},
    },
    "sla": {"freshness_hours": 25, "quality_threshold_pct": 95.0},
}


def register_contract(contract: Dict[str, Any], bucket: str) -> bool:
    s3 = boto3.client("s3")
    contract_id = str(contract["contract_id"])
    version = str(contract["version"])
    key = f"data_contracts/{contract_id}/{version}.json"
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(contract))
    logger.info(f"Contract registered: {contract_id} v{version}")
    return True


def get_contract(
    contract_id: str, version: str, bucket: str
) -> Optional[Dict[str, Any]]:
    s3 = boto3.client("s3")
    key = f"data_contracts/{contract_id}/{version}.json"
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        contract = json.loads(response["Body"].read())
        logger.info(f"Contract loaded: {contract_id} v{version}")
        return contract
    except Exception:
        logger.info(f"Contract not found: {contract_id} v{version}")
        return None


def validate_against_contract(
    data: Dict[str, Any], contract: Dict[str, Any]
) -> Dict[str, Any]:
    schema = contract.get("schema", {})
    contract_id = str(contract.get("contract_id", ""))
    violations: List[str] = []

    for field, rules in schema.items():
        required = bool(rules.get("required", False))
        if required and field not in data:
            violations.append(f"Missing required field: {field}")
            continue

        if field not in data:
            continue

        value = data[field]
        field_type = str(rules.get("type", ""))

        if field_type == "string" and not isinstance(value, str):
            violations.append(f"Field {field} must be string")
        elif field_type == "float" and not isinstance(value, (int, float)):
            violations.append(f"Field {field} must be float")
        elif field_type == "integer" and not isinstance(value, int):
            violations.append(f"Field {field} must be integer")

        if "min" in rules and isinstance(value, (int, float)):
            if float(str(value)) < float(str(rules["min"])):
                violations.append(f"Field {field} below minimum {rules['min']}")

    valid = len(violations) == 0
    logger.info(f"Contract {contract_id} validation: valid={valid}, violations={len(violations)}")
    return {"valid": valid, "violations": violations, "contract_id": contract_id}


def check_contract_compatibility(
    old_contract: Dict[str, Any], new_contract: Dict[str, Any]
) -> Dict[str, Any]:
    old_schema = old_contract.get("schema", {})
    new_schema = new_contract.get("schema", {})
    breaking_changes: List[str] = []

    for field, rules in old_schema.items():
        if bool(rules.get("required", False)) and field not in new_schema:
            breaking_changes.append(f"Removed required field: {field}")
            continue
        if field in new_schema:
            old_type = str(rules.get("type", ""))
            new_type = str(new_schema[field].get("type", ""))
            if old_type != new_type:
                breaking_changes.append(f"Type changed for {field}: {old_type} -> {new_type}")

    compatible = len(breaking_changes) == 0
    logger.info(f"Compatibility check: compatible={compatible}, breaking={len(breaking_changes)}")
    return {"compatible": compatible, "breaking_changes": breaking_changes}


def list_contracts(bucket: str) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3")
    prefix = "data_contracts/"
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    contracts = []
    for obj in response.get("Contents", []):
        key = str(obj["Key"])
        resp = s3.get_object(Bucket=bucket, Key=key)
        contract = json.loads(resp["Body"].read())
        contracts.append(contract)
    logger.info(f"Found {len(contracts)} contracts")
    return contracts


def run_contract_registration(bucket: str) -> None:
    register_contract(STOCK_PRICE_CONTRACT, bucket)
    logger.info("Contract Registration Complete")


if __name__ == "__main__":
    pass
