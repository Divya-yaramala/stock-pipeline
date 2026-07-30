import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_entity(
    entity_id: str,
    entity_type: str,
    properties: Dict[str, Any],
    bucket: str,
) -> bool:
    record: Dict[str, Any] = {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "properties": properties,
        "created_at": datetime.utcnow().isoformat(),
    }
    try:
        s3 = boto3.client("s3")
        key = f"knowledge_graph/entities/{entity_type}/{entity_id}.json"
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(record),
            ContentType="application/json",
        )
        logger.info(f"Entity added: {entity_type}/{entity_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to add entity {entity_id}: {e}")
        return False


def add_relationship(
    source_id: str,
    target_id: str,
    relationship_type: str,
    properties: Optional[Dict[str, Any]],
    bucket: str,
) -> str:
    rel_id = hashlib.md5(f"{source_id}:{relationship_type}:{target_id}".encode()).hexdigest()
    record: Dict[str, Any] = {
        "relationship_id": rel_id,
        "source_id": source_id,
        "target_id": target_id,
        "relationship_type": relationship_type,
        "properties": properties or {},
        "created_at": datetime.utcnow().isoformat(),
    }
    try:
        s3 = boto3.client("s3")
        key = f"knowledge_graph/relationships/{relationship_type}/{rel_id}.json"
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(record),
            ContentType="application/json",
        )
        logger.info(f"Relationship added: {source_id} -{relationship_type}-> {target_id}")
    except Exception as e:
        logger.error(f"Failed to add relationship: {e}")
    return rel_id


def get_entity_relationships(
    entity_id: str,
    bucket: str,
) -> List[Dict[str, Any]]:
    relationships: List[Dict[str, Any]] = []
    try:
        s3 = boto3.client("s3")
        prefix = "knowledge_graph/relationships/"
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                try:
                    body = s3.get_object(Bucket=bucket, Key=str(obj["Key"]))["Body"].read()
                    rel = json.loads(body.decode("utf-8"))
                    if (
                        str(rel.get("source_id")) == entity_id
                        or str(rel.get("target_id")) == entity_id
                    ):
                        relationships.append(rel)
                except Exception:
                    continue
    except Exception as e:
        logger.error(f"Failed to get relationships for {entity_id}: {e}")
    logger.info(f"Found {len(relationships)} relationships for {entity_id}")
    return relationships


def find_connected_entities(
    entity_id: str,
    relationship_type: str,
    bucket: str,
) -> List[str]:
    connected: List[str] = []
    try:
        s3 = boto3.client("s3")
        prefix = f"knowledge_graph/relationships/{relationship_type}/"
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                try:
                    body = s3.get_object(Bucket=bucket, Key=str(obj["Key"]))["Body"].read()
                    rel = json.loads(body.decode("utf-8"))
                    if str(rel.get("source_id")) == entity_id:
                        connected.append(str(rel["target_id"]))
                    elif str(rel.get("target_id")) == entity_id:
                        connected.append(str(rel["source_id"]))
                except Exception:
                    continue
    except Exception as e:
        logger.error(f"Failed to find connected entities: {e}")
    logger.info(
        f"Found {len(connected)} connected entities for {entity_id} via {relationship_type}"
    )
    return connected


def build_stock_knowledge_graph(bucket: str) -> Dict[str, Any]:
    entities = [
        ("AAPL", "stock", {"name": "Apple Inc.", "sector": "Technology"}),
        ("MSFT", "stock", {"name": "Microsoft Corp.", "sector": "Technology"}),
        ("GOOGL", "stock", {"name": "Alphabet Inc.", "sector": "Communication Services"}),
        ("AMZN", "stock", {"name": "Amazon.com Inc.", "sector": "Consumer Discretionary"}),
        ("TSLA", "stock", {"name": "Tesla Inc.", "sector": "Consumer Discretionary"}),
        ("Technology", "sector", {"description": "Technology companies"}),
        ("Communication Services", "sector", {"description": "Communication services companies"}),
        ("Consumer Discretionary", "sector", {"description": "Consumer discretionary companies"}),
        ("US_MARKET", "market", {"description": "US stock market"}),
    ]

    relationships = [
        ("AAPL", "Technology", "BELONGS_TO", {}),
        ("MSFT", "Technology", "BELONGS_TO", {}),
        ("GOOGL", "Communication Services", "BELONGS_TO", {}),
        ("AMZN", "Consumer Discretionary", "BELONGS_TO", {}),
        ("TSLA", "Consumer Discretionary", "BELONGS_TO", {}),
        ("AAPL", "MSFT", "COMPETES_WITH", {"reason": "same sector"}),
        ("AAPL", "MSFT", "CORRELATES_WITH", {"correlation": "high"}),
    ]

    entities_created = 0
    relationships_created = 0

    for eid, etype, props in entities:
        if add_entity(eid, etype, props, bucket):
            entities_created += 1

    for src, tgt, rtype, props in relationships:
        add_relationship(src, tgt, rtype, props, bucket)
        relationships_created += 1

    result: Dict[str, Any] = {
        "entities_created": entities_created,
        "relationships_created": relationships_created,
    }
    logger.info("Knowledge Graph Built")
    return result


if __name__ == "__main__":
    pass
