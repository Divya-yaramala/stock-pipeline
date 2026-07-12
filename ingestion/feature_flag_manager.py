import json
import logging
from datetime import datetime
from typing import Any, Dict

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_FLAGS: Dict[str, Any] = {
    "enable_gpt_insights": True,
    "enable_kafka_streaming": False,
    "enable_chaos_engineering": False,
    "enable_ensemble_models": True,
    "enable_news_sentiment": True,
    "enable_slack_alerts": True,
    "enable_email_reports": True,
    "enable_snowflake_sync": True,
    "enable_auto_remediation": True,
    "enable_ab_testing": False,
}

FLAGS_S3_KEY = "feature_flags/flags.json"


def load_feature_flags(bucket: str) -> Dict[str, Any]:
    try:
        client = boto3.client("s3")
        response = client.get_object(Bucket=bucket, Key=FLAGS_S3_KEY)
        s3_flags: Dict[str, Any] = json.loads(response["Body"].read().decode("utf-8"))
        merged = {**DEFAULT_FLAGS, **s3_flags}
        logger.info("Loaded %d feature flags from S3", len(merged))
        return merged
    except Exception:
        logger.info("No S3 flags found, using defaults (%d flags)", len(DEFAULT_FLAGS))
        return dict(DEFAULT_FLAGS)


def save_feature_flags(flags: Dict[str, Any], bucket: str) -> bool:
    try:
        client = boto3.client("s3")
        client.put_object(
            Bucket=bucket,
            Key=FLAGS_S3_KEY,
            Body=json.dumps(flags, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Saved %d feature flags to S3", len(flags))
        return True
    except Exception as e:
        logger.error("Failed to save feature flags: %s", str(e))
        return False


def is_enabled(flag_name: str, bucket: str, default: bool = False) -> bool:
    flags = load_feature_flags(bucket)
    result = bool(flags.get(flag_name, default))
    logger.info("Flag check: %s = %s", flag_name, result)
    return result


def enable_flag(flag_name: str, bucket: str) -> bool:
    flags = load_feature_flags(bucket)
    flags[flag_name] = True
    success = save_feature_flags(flags, bucket)
    if success:
        logger.info("Flag enabled: %s", flag_name)
    return success


def disable_flag(flag_name: str, bucket: str) -> bool:
    flags = load_feature_flags(bucket)
    flags[flag_name] = False
    success = save_feature_flags(flags, bucket)
    if success:
        logger.info("Flag disabled: %s", flag_name)
    return success


def get_all_flags(bucket: str) -> Dict[str, Any]:
    flags = load_feature_flags(bucket)
    enabled_count = sum(1 for v in flags.values() if v is True)
    logger.info("Flag summary: %d total, %d enabled", len(flags), enabled_count)
    return flags


def run_flag_audit(bucket: str) -> Dict[str, Any]:
    flags = load_feature_flags(bucket)
    enabled = [k for k, v in flags.items() if v is True]
    disabled = [k for k, v in flags.items() if v is False]
    overridden = [k for k in flags if k in DEFAULT_FLAGS and flags[k] != DEFAULT_FLAGS[k]]
    audit: Dict[str, Any] = {
        "total": int(len(flags)),
        "enabled": int(len(enabled)),
        "disabled": int(len(disabled)),
        "overridden": overridden,
        "audited_at": str(datetime.utcnow().isoformat()),
    }
    logger.info(
        "Flag audit: %d total, %d enabled, %d disabled, %d overridden",
        audit["total"],
        audit["enabled"],
        audit["disabled"],
        len(overridden),
    )
    return audit


if __name__ == "__main__":
    pass
