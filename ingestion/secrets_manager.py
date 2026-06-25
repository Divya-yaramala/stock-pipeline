import base64
import datetime
import hashlib
import json
import logging
import os

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ENCRYPTION_KEY = os.environ.get("SECRETS_KEY", "default-dev-key-change-in-prod")


def encrypt_value(value: str, key: str) -> str:
    key_bytes = hashlib.sha256(key.encode()).digest()
    value_bytes = value.encode()
    encrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(value_bytes))
    result = base64.b64encode(encrypted).decode()
    logger.info("Value encrypted")
    return result


def decrypt_value(encrypted: str, key: str) -> str:
    key_bytes = hashlib.sha256(key.encode()).digest()
    encrypted_bytes = base64.b64decode(encrypted.encode())
    decrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted_bytes))
    result = decrypted.decode()
    logger.info("Value decrypted")
    return result


def store_secret(secret_name: str, secret_value: str, bucket: str) -> bool:
    s3 = boto3.client("s3")
    try:
        encrypted = encrypt_value(secret_value, ENCRYPTION_KEY)
        payload = {
            "secret_name": secret_name,
            "encrypted_value": encrypted,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        key = f"secrets/{secret_name}.json"
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload))
        logger.info(f"Secret stored: {secret_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to store secret {secret_name}: {e}")
        return False


def get_secret(secret_name: str, bucket: str) -> str:
    s3 = boto3.client("s3")
    try:
        key = f"secrets/{secret_name}.json"
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        payload = json.loads(body)
        decrypted = decrypt_value(payload["encrypted_value"], ENCRYPTION_KEY)
        logger.info(f"Secret retrieved: {secret_name}")
        return decrypted
    except Exception as e:
        logger.error(f"Failed to get secret {secret_name}: {e}")
        return ""


def rotate_secret(secret_name: str, new_value: str, bucket: str) -> bool:
    s3 = boto3.client("s3")
    try:
        encrypted = encrypt_value(new_value, ENCRYPTION_KEY)
        payload = {
            "secret_name": secret_name,
            "encrypted_value": encrypted,
            "rotated_at": datetime.datetime.utcnow().isoformat(),
        }
        key = f"secrets/{secret_name}.json"
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload))
        logger.info(f"Secret rotated: {secret_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to rotate secret {secret_name}: {e}")
        return False


def list_secrets(bucket: str) -> list:
    s3 = boto3.client("s3")
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix="secrets/")
        objects = response.get("Contents", [])
        names = []
        for obj in objects:
            key = obj["Key"]
            if key.startswith("secrets/") and key.endswith(".json") and "/audit/" not in key:
                name = key[len("secrets/") : -len(".json")]
                names.append(name)
        logger.info(f"Listed {len(names)} secrets")
        return names
    except Exception as e:
        logger.error(f"Failed to list secrets: {e}")
        return []


def audit_secret_access(secret_name: str, action: str, bucket: str) -> bool:
    s3 = boto3.client("s3")
    try:
        now = datetime.datetime.utcnow()
        timestamp = now.strftime("%H%M%S%f")
        key = f"secrets/audit/{now.year:04d}/{now.month:02d}/{now.day:02d}/{timestamp}.json"
        record = {
            "secret_name": secret_name,
            "action": action,
            "timestamp": now.isoformat(),
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(record))
        logger.info(f"Audit logged: {action} on {secret_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to audit secret access: {e}")
        return False


if __name__ == "__main__":
    pass
