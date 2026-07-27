import datetime
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_data_product_schema(
    product_id: str,
    bucket: str,
) -> Optional[Dict[str, Any]]:
    s3 = boto3.client("s3")
    key = f"data_contracts/{product_id}/schema.json"
    try:
        resp = s3.get_object(Bucket=bucket, Key=key)
        schema = json.loads(resp["Body"].read())
        logger.info(f"Schema retrieved: {product_id}")
        return schema
    except Exception as e:
        logger.warning(f"Schema not found for {product_id}: {e}")
        return None


def request_data_access(
    product_id: str,
    requester: str,
    purpose: str,
    bucket: str,
) -> str:
    s3 = boto3.client("s3")
    request_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow()
    timestamp = now.strftime("%Y%m%dT%H%M%S")

    record = {
        "request_id": request_id,
        "product_id": product_id,
        "requester": requester,
        "purpose": purpose,
        "status": "pending",
        "requested_at": now.isoformat(),
    }
    key = f"data_mesh/access_requests/{product_id}/{requester}_{timestamp}.json"
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(record))
    logger.info(f"Access request created: {request_id} | {product_id} | {requester}")
    return request_id


def approve_access_request(
    request_id: str,
    approver: str,
    bucket: str,
) -> bool:
    s3 = boto3.client("s3")
    now = datetime.datetime.utcnow()
    timestamp = now.strftime("%Y%m%dT%H%M%S")

    approval = {
        "request_id": request_id,
        "approver": approver,
        "status": "approved",
        "approved_at": now.isoformat(),
    }
    key = f"data_mesh/approvals/{request_id}/approval_{timestamp}.json"
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(approval))
        logger.info(f"Access request approved: {request_id} by {approver}")
        return True
    except Exception as e:
        logger.error(f"Failed to approve request {request_id}: {e}")
        return False


def get_data_product_sample(
    product_id: str,
    num_records: int,
    bucket: str,
) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3")
    prefix = f"data_mesh/samples/{product_id}/"
    samples: List[Dict[str, Any]] = []
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        for obj in response.get("Contents", []):
            if len(samples) >= num_records:
                break
            key = str(obj["Key"])
            resp = s3.get_object(Bucket=bucket, Key=key)
            record = json.loads(resp["Body"].read())
            if isinstance(record, list):
                samples.extend(record[:num_records - len(samples)])
            else:
                samples.append(record)
    except Exception as e:
        logger.error(f"Failed to get sample for {product_id}: {e}")

    logger.info(f"Sample retrieved: {product_id} | {len(samples)} records")
    return samples[:num_records]


def publish_data_product_update(
    product_id: str,
    version: str,
    changelog: str,
    bucket: str,
) -> bool:
    s3 = boto3.client("s3")
    now = datetime.datetime.utcnow()
    update = {
        "product_id": product_id,
        "version": version,
        "changelog": changelog,
        "published_at": now.isoformat(),
    }
    key = f"data_mesh/updates/{product_id}/{version}.json"
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(update))
        logger.info(f"Product update published: {product_id} v{version}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish update for {product_id}: {e}")
        return False


def run_data_mesh_api_demo(bucket: str) -> Dict[str, Any]:
    request_id = request_data_access(
        product_id="DP001",
        requester="analytics_team",
        purpose="Demo access request",
        bucket=bucket,
    )

    logger.info("Data Mesh API Demo Complete")
    return {"request_id": request_id, "status": "demo_complete"}


if __name__ == "__main__":
    pass
