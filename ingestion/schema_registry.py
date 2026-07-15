import datetime
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def register_schema(
    schema_name: str,
    schema_def: Dict[str, Any],
    version: str,
    bucket: str,
) -> str:
    s3 = boto3.client("s3")
    registered_at = datetime.datetime.utcnow().isoformat()
    schema_id = hashlib.md5(f"{schema_name}:{version}:{registered_at}".encode()).hexdigest()
    record: Dict[str, Any] = {
        "schema_id": schema_id,
        "schema_name": schema_name,
        "schema_def": schema_def,
        "version": version,
        "registered_at": registered_at,
    }
    key = f"schema_registry/{schema_name}/{version}.json"
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(record))
    logger.info(f"Schema registered: {schema_name} v{version} id={schema_id}")
    return schema_id


def get_schema(
    schema_name: str, version: str, bucket: str
) -> Optional[Dict[str, Any]]:
    s3 = boto3.client("s3")
    key = f"schema_registry/{schema_name}/{version}.json"
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        schema = json.loads(response["Body"].read())
        logger.info(f"Schema loaded: {schema_name} v{version}")
        return schema
    except Exception:
        logger.info(f"Schema not found: {schema_name} v{version}")
        return None


def get_latest_schema(
    schema_name: str, bucket: str
) -> Optional[Dict[str, Any]]:
    s3 = boto3.client("s3")
    prefix = f"schema_registry/{schema_name}/"
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    contents = response.get("Contents", [])
    if not contents:
        return None
    latest_key = str(sorted(contents, key=lambda x: str(x["Key"]))[-1]["Key"])
    resp = s3.get_object(Bucket=bucket, Key=latest_key)
    schema = json.loads(resp["Body"].read())
    logger.info(f"Latest schema for {schema_name}: {schema.get('version')}")
    return schema


def list_schemas(bucket: str) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3")
    prefix = "schema_registry/"
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    schemas = []
    for obj in response.get("Contents", []):
        key = str(obj["Key"])
        resp = s3.get_object(Bucket=bucket, Key=key)
        schema = json.loads(resp["Body"].read())
        schemas.append(schema)
    logger.info(f"Found {len(schemas)} schemas")
    return schemas


def validate_schema_evolution(
    old_schema: Dict[str, Any], new_schema: Dict[str, Any]
) -> Dict[str, Any]:
    old_fields = set(old_schema.keys())
    new_fields = set(new_schema.keys())
    changes: List[str] = []
    breaking: List[str] = []

    for field in old_fields - new_fields:
        breaking.append(f"Removed field: {field}")
        changes.append(f"BREAKING — removed field: {field}")

    for field in new_fields - old_fields:
        changes.append(f"Added field: {field}")

    for field in old_fields & new_fields:
        old_type = str(old_schema[field].get("type", "")) if isinstance(old_schema[field], dict) else ""
        new_type = str(new_schema[field].get("type", "")) if isinstance(new_schema[field], dict) else ""
        if old_type and new_type and old_type != new_type:
            breaking.append(f"Type changed for {field}: {old_type} -> {new_type}")
            changes.append(f"BREAKING — type changed for {field}: {old_type} -> {new_type}")

    safe = len(breaking) == 0
    return {"safe": safe, "changes": changes, "breaking": breaking}


def run_schema_registry_setup(bucket: str) -> None:
    schemas = [
        ("stock_prices_raw", {"ticker": {"type": "string"}, "close_price": {"type": "float"}}, "1.0.0"),
        ("stock_anomalies", {"ticker": {"type": "string"}, "is_anomaly": {"type": "boolean"}}, "1.0.0"),
        ("stock_predictions", {"ticker": {"type": "string"}, "forecast_price": {"type": "float"}}, "1.0.0"),
        ("stock_sentiment", {"ticker": {"type": "string"}, "sentiment": {"type": "string"}}, "1.0.0"),
    ]
    for name, schema_def, version in schemas:
        register_schema(name, schema_def, version, bucket)
    logger.info("Schema Registry Setup Complete")


if __name__ == "__main__":
    pass
