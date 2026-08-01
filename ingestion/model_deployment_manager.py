import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEPLOYMENT_ENVIRONMENTS: List[Dict[str, Any]] = [
    {"env_id": "E001", "name": "development", "auto_promote": False, "min_accuracy": 0.60},
    {"env_id": "E002", "name": "staging", "auto_promote": False, "min_accuracy": 0.65},
    {"env_id": "E003", "name": "production", "auto_promote": False, "min_accuracy": 0.70},
]

_ENV_MAP: Dict[str, Dict[str, Any]] = {str(e["name"]): e for e in DEPLOYMENT_ENVIRONMENTS}


def create_deployment(
    model_name: str,
    model_version: str,
    environment: str,
    metrics: Dict[str, float],
    bucket: str,
) -> str:
    if environment not in _ENV_MAP:
        raise ValueError(f"Invalid environment: {environment!r}. Must be one of {list(_ENV_MAP)}")

    env_cfg = _ENV_MAP[environment]
    min_acc = float(str(env_cfg["min_accuracy"]))
    accuracy = float(str(metrics.get("accuracy", 0.0)))
    if accuracy < min_acc:
        raise ValueError(f"Accuracy {accuracy:.2f} below minimum {min_acc:.2f} for {environment}")

    deployment_id = hashlib.md5(
        f"{model_name}:{model_version}:{environment}:{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()

    record: Dict[str, Any] = {
        "deployment_id": deployment_id,
        "model_name": model_name,
        "model_version": model_version,
        "environment": environment,
        "metrics": metrics,
        "status": "active",
        "deployed_at": datetime.utcnow().isoformat(),
    }

    try:
        s3 = boto3.client("s3")
        key = f"deployments/{environment}/{model_name}/{deployment_id}.json"
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(record),
            ContentType="application/json",
        )
        logger.info(f"Deployment created: {deployment_id} ({model_name} → {environment})")
    except Exception as e:
        logger.error(f"Failed to save deployment: {e}")

    return deployment_id


def promote_to_environment(
    deployment_id: str,
    from_env: str,
    to_env: str,
    bucket: str,
) -> bool:
    try:
        s3 = boto3.client("s3")
        source_prefix = f"deployments/{from_env}/"
        paginator = s3.get_paginator("list_objects_v2")
        deployment: Optional[Dict[str, Any]] = None

        for page in paginator.paginate(Bucket=bucket, Prefix=source_prefix):
            for obj in page.get("Contents", []):
                if deployment_id in str(obj["Key"]):
                    body = s3.get_object(Bucket=bucket, Key=str(obj["Key"]))["Body"].read()
                    deployment = json.loads(body.decode("utf-8"))
                    break
            if deployment:
                break

        if not deployment:
            logger.error(f"Deployment {deployment_id} not found in {from_env}")
            return False

        create_deployment(
            model_name=str(deployment["model_name"]),
            model_version=str(deployment["model_version"]),
            environment=to_env,
            metrics={k: float(str(v)) for k, v in deployment.get("metrics", {}).items()},
            bucket=bucket,
        )
        logger.info(f"Promotion complete: {deployment_id} {from_env} → {to_env}")
        return True
    except Exception as e:
        logger.error(f"Promotion failed: {e}")
        return False


def rollback_deployment(
    model_name: str,
    environment: str,
    bucket: str,
) -> bool:
    try:
        s3 = boto3.client("s3")
        prefix = f"deployments/{environment}/{model_name}/"
        paginator = s3.get_paginator("list_objects_v2")
        deployments: List[Dict[str, Any]] = []

        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                try:
                    body = s3.get_object(Bucket=bucket, Key=str(obj["Key"]))["Body"].read()
                    deployments.append(json.loads(body.decode("utf-8")))
                except Exception:
                    continue

        deployments.sort(key=lambda d: str(d.get("deployed_at", "")), reverse=True)

        if len(deployments) < 2:
            logger.warning(f"No previous deployment to roll back to for {model_name}/{environment}")
            return False

        previous = deployments[1]
        previous["status"] = "active"
        key = (
            f"deployments/{environment}/{model_name}"
            f"/rollback_{str(previous['deployment_id'])}.json"
        )
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(previous),
            ContentType="application/json",
        )
        logger.info(f"Rollback performed: {model_name}/{environment} → {previous['model_version']}")
        return True
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return False


def get_active_deployment(
    model_name: str,
    environment: str,
    bucket: str,
) -> Optional[Dict[str, Any]]:
    try:
        s3 = boto3.client("s3")
        prefix = f"deployments/{environment}/{model_name}/"
        paginator = s3.get_paginator("list_objects_v2")
        deployments: List[Dict[str, Any]] = []

        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                try:
                    body = s3.get_object(Bucket=bucket, Key=str(obj["Key"]))["Body"].read()
                    d = json.loads(body.decode("utf-8"))
                    if str(d.get("status")) == "active":
                        deployments.append(d)
                except Exception:
                    continue

        if not deployments:
            logger.info(f"No active deployment for {model_name}/{environment}")
            return None

        deployments.sort(key=lambda d: str(d.get("deployed_at", "")), reverse=True)
        active = deployments[0]
        logger.info(f"Active deployment found: {active.get('deployment_id')}")
        return active
    except Exception as e:
        logger.error(f"Failed to get active deployment: {e}")
        return None


def list_deployments(
    environment: str,
    bucket: str,
) -> List[Dict[str, Any]]:
    deployments: List[Dict[str, Any]] = []
    try:
        s3 = boto3.client("s3")
        prefix = f"deployments/{environment}/"
        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                try:
                    body = s3.get_object(Bucket=bucket, Key=str(obj["Key"]))["Body"].read()
                    deployments.append(json.loads(body.decode("utf-8")))
                except Exception:
                    continue
    except Exception as e:
        logger.error(f"Failed to list deployments: {e}")

    logger.info(f"Found {len(deployments)} deployments in {environment}")
    return deployments


def run_deployment_check(bucket: str) -> Dict[str, Any]:
    environments: Dict[str, int] = {}
    total = 0

    for env in DEPLOYMENT_ENVIRONMENTS:
        env_name = str(env["name"])
        deps = list_deployments(env_name, bucket)
        environments[env_name] = len(deps)
        total += len(deps)

    result: Dict[str, Any] = {"environments": environments, "total_deployments": total}
    logger.info(f"Deployment check summary: {total} total across {len(environments)} environments")
    return result


if __name__ == "__main__":
    pass
