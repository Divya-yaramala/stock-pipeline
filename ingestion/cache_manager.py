import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from functools import wraps

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_cache_key(func_name: str, args: dict) -> str:
    raw = json.dumps({"func": func_name, "args": args}, sort_keys=True)
    key = hashlib.md5(raw.encode()).hexdigest()[:16]
    logger.info(f"Cache key generated: {key} for {func_name}")
    return key


def get_from_cache(cache_key: str, bucket: str) -> dict:
    s3 = boto3.client("s3")
    s3_key = f"cache/{cache_key}.json"
    try:
        response = s3.get_object(Bucket=bucket, Key=s3_key)
        entry = json.loads(response["Body"].read())
        expires_at = datetime.fromisoformat(entry["expires_at"])
        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            logger.info(f"Cache miss (expired): {cache_key}")
            return None
        logger.info(f"Cache hit: {cache_key}")
        return entry["data"]
    except Exception:
        logger.info(f"Cache miss (not found): {cache_key}")
        return None


def save_to_cache(cache_key: str, data: dict, bucket: str, ttl_seconds: int = 3600) -> bool:
    s3 = boto3.client("s3")
    s3_key = f"cache/{cache_key}.json"
    now = datetime.now(timezone.utc)
    expires_at = datetime.fromtimestamp(now.timestamp() + ttl_seconds, tz=timezone.utc)
    entry = {
        "data": data,
        "cached_at": now.isoformat(),
        "ttl_seconds": ttl_seconds,
        "expires_at": expires_at.isoformat(),
    }
    try:
        s3.put_object(Bucket=bucket, Key=s3_key, Body=json.dumps(entry))
        logger.info(f"Cache saved: {cache_key}, expires at {expires_at.isoformat()}")
        return True
    except Exception as e:
        logger.error(f"Failed to save cache {cache_key}: {e}")
        return False


def invalidate_cache(cache_key: str, bucket: str) -> bool:
    s3 = boto3.client("s3")
    s3_key = f"cache/{cache_key}.json"
    try:
        s3.delete_object(Bucket=bucket, Key=s3_key)
        logger.info(f"Cache invalidated: {cache_key}")
        return True
    except Exception as e:
        logger.error(f"Failed to invalidate cache {cache_key}: {e}")
        return False


def clear_expired_cache(bucket: str) -> int:
    s3 = boto3.client("s3")
    now = datetime.now(timezone.utc)
    deleted = 0
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix="cache/"):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                try:
                    response = s3.get_object(Bucket=bucket, Key=key)
                    entry = json.loads(response["Body"].read())
                    expires_at = datetime.fromisoformat(entry["expires_at"])
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    if now > expires_at:
                        s3.delete_object(Bucket=bucket, Key=key)
                        deleted += 1
                except Exception:
                    continue
    except Exception as e:
        logger.error(f"Error clearing expired cache: {e}")
    logger.info(f"Cleared {deleted} expired cache entries")
    return deleted


def cache_decorator(ttl_seconds: int = 3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            bucket = os.getenv("S3_BUCKET", "stock-pipeline-bucket")
            cache_args = {"args": str(args), "kwargs": str(kwargs)}
            cache_key = generate_cache_key(func.__name__, cache_args)
            cached = get_from_cache(cache_key, bucket)
            if cached is not None:
                return cached
            result = func(*args, **kwargs)
            save_to_cache(cache_key, result, bucket, ttl_seconds)
            return result

        return wrapper

    return decorator


if __name__ == "__main__":
    pass
