import hashlib
import json
import logging
import os
from datetime import datetime

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def register_model(
    model_name: str,
    model_version: str,
    model_params: dict,
    model_metrics: dict,
    bucket: str,
) -> str:
    """
    Register a new ML model version in the S3 registry.

    Args:
        model_name: Name of the model.
        model_version: Version string (e.g., "v1.0.0").
        model_params: Dictionary of model hyperparameters.
        model_metrics: Dictionary of model evaluation metrics.
        bucket: S3 bucket name.

    Returns:
        model_id string (MD5 hash of name+version+timestamp).
    """
    timestamp = datetime.utcnow().isoformat()
    raw = f"{model_name}{model_version}{timestamp}"
    model_id = hashlib.md5(raw.encode()).hexdigest()

    record = {
        "model_id": model_id,
        "model_name": model_name,
        "model_version": model_version,
        "model_params": model_params,
        "model_metrics": model_metrics,
        "registered_at": timestamp,
        "status": "active",
    }

    key = f"models/registry/{model_name}/{model_version}/metadata.json"
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(record),
        ContentType="application/json",
    )
    logger.info("Registered model %s version %s with ID %s", model_name, model_version, model_id)
    return model_id


def get_model_metadata(
    model_name: str,
    model_version: str,
    bucket: str,
) -> dict:
    """
    Load model metadata from S3.

    Args:
        model_name: Name of the model.
        model_version: Version string.
        bucket: S3 bucket name.

    Returns:
        Metadata dict, or empty dict if not found.
    """
    key = f"models/registry/{model_name}/{model_version}/metadata.json"
    s3 = boto3.client("s3")
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        metadata = json.loads(response["Body"].read().decode("utf-8"))
        return metadata
    except Exception:
        return {}


def list_model_versions(
    model_name: str,
    bucket: str,
) -> list:
    """
    List all registered versions for a model.

    Args:
        model_name: Name of the model.
        bucket: S3 bucket name.

    Returns:
        List of version strings.
    """
    prefix = f"models/registry/{model_name}/"
    s3 = boto3.client("s3")
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")

    versions = []
    for prefix_obj in response.get("CommonPrefixes", []):
        parts = prefix_obj["Prefix"].rstrip("/").split("/")
        versions.append(parts[-1])

    logger.info("Found %d versions for model %s", len(versions), model_name)
    return versions


def promote_model(
    model_name: str,
    model_version: str,
    bucket: str,
    stage: str = "production",
) -> bool:
    """
    Promote a model version to a lifecycle stage.

    Args:
        model_name: Name of the model.
        model_version: Version string.
        bucket: S3 bucket name.
        stage: Target stage — staging, production, or archived.

    Returns:
        True on success, False on failure.
    """
    try:
        metadata = get_model_metadata(model_name, model_version, bucket)
        metadata["status"] = stage
        metadata["promoted_at"] = datetime.utcnow().isoformat()

        key = f"models/registry/{model_name}/{model_version}/metadata.json"
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(metadata),
            ContentType="application/json",
        )
        logger.info("Promoted model %s version %s to %s", model_name, model_version, stage)
        return True
    except Exception as e:
        logger.error("Failed to promote model %s/%s: %s", model_name, model_version, e)
        return False


def get_production_model(
    model_name: str,
    bucket: str,
) -> dict:
    """
    Get the current production model metadata for a given model name.

    Args:
        model_name: Name of the model.
        bucket: S3 bucket name.

    Returns:
        Metadata dict for the production model, or empty dict if none found.
    """
    versions = list_model_versions(model_name, bucket)
    for version in versions:
        metadata = get_model_metadata(model_name, version, bucket)
        if metadata.get("status") == "production":
            logger.info("Production model %s is version %s", model_name, version)
            return metadata
    return {}


def run_model_registry_check() -> None:
    """List all registered models in the bucket and log a summary."""
    bucket = os.getenv("AWS_S3_BUCKET", "")
    s3 = boto3.client("s3")
    prefix = "models/registry/"
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")

    models = [p["Prefix"].rstrip("/").split("/")[-1] for p in response.get("CommonPrefixes", [])]
    logger.info("Model registry check: %d models registered — %s", len(models), models)


if __name__ == "__main__":
    run_model_registry_check()
