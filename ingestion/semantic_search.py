import json
import logging
import math
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_STOPWORDS = {"the", "a", "an", "and", "or", "in", "of", "to", "is", "for", "with", "on", "at"}


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def build_search_index(
    documents: List[Dict[str, Any]],
    bucket: str,
) -> Dict[str, Any]:
    index: Dict[str, List[str]] = {}

    for doc in documents:
        doc_id = str(doc.get("id", ""))
        text = str(doc.get("text", ""))
        for term in _tokenize(text):
            if term not in index:
                index[term] = []
            if doc_id not in index[term]:
                index[term].append(doc_id)

    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key="search/index/index.json",
            Body=json.dumps(index),
            ContentType="application/json",
        )
    except Exception as e:
        logger.error(f"Failed to save search index: {e}")

    result: Dict[str, Any] = {
        "indexed_documents": len(documents),
        "unique_terms": len(index),
    }
    logger.info(f"Search index built: {len(documents)} docs, {len(index)} unique terms")
    return result


def search_documents(
    query: str,
    bucket: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    query_terms = _tokenize(query)
    scores: Dict[str, int] = {}

    try:
        s3 = boto3.client("s3")
        body = s3.get_object(Bucket=bucket, Key="search/index/index.json")["Body"].read()
        index: Dict[str, List[str]] = json.loads(body.decode("utf-8"))
        for term in query_terms:
            for doc_id in index.get(term, []):
                scores[doc_id] = scores.get(doc_id, 0) + 1
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    results = [{"id": doc_id, "score": score} for doc_id, score in ranked]
    logger.info(f"Search returned {len(results)} results for query: {query!r}")
    return results


def index_pipeline_docs(bucket: str) -> Dict[str, Any]:
    documents: List[Dict[str, Any]] = [
        {
            "id": "adr-001",
            "text": "Why Apache Airflow over Prefect orchestration DAG tasks scheduling",
            "metadata": {"type": "adr"},
        },
        {
            "id": "adr-004",
            "text": "Isolation Forest anomaly detection unsupervised machine learning OHLCV",
            "metadata": {"type": "adr"},
        },
        {
            "id": "adr-005",
            "text": "Prophet time series price prediction forecasting trend seasonality",
            "metadata": {"type": "adr"},
        },
        {
            "id": "module-anomaly-detector",
            "text": "anomaly detector isolation forest score threshold alert detection",
            "metadata": {"type": "module"},
        },
        {
            "id": "module-price-predictor",
            "text": "price predictor prophet forecast confidence bounds future prices",
            "metadata": {"type": "module"},
        },
        {
            "id": "module-data-validator",
            "text": "data validator quality checks completeness schema freshness score",
            "metadata": {"type": "module"},
        },
        {
            "id": "module-sla-monitor",
            "text": "sla monitor service level agreement compliance tracking pipeline",
            "metadata": {"type": "module"},
        },
        {
            "id": "readme-architecture",
            "text": "pipeline architecture airflow dbt snowflake s3 postgres API dashboard",
            "metadata": {"type": "readme"},
        },
    ]

    result = build_search_index(documents, bucket)
    logger.info("Pipeline Docs Indexed")
    return result


def search_pipeline_knowledge(
    query: str,
    bucket: str,
) -> List[Dict[str, Any]]:
    results = search_documents(query, bucket, top_k=5)
    logger.info(f"Pipeline knowledge search complete for: {query!r}")
    return results


def recommend_related_modules(
    module_name: str,
    bucket: str,
) -> List[str]:
    results = search_documents(module_name.replace("_", " "), bucket, top_k=5)
    related: List[str] = []
    for r in results:
        doc_id = str(r.get("id", ""))
        if doc_id.startswith("module-") and module_name not in doc_id:
            name = doc_id.replace("module-", "").replace("-", "_")
            if name not in related:
                related.append(name)
    logger.info(f"Recommended {len(related)} related modules for {module_name}")
    return related


if __name__ == "__main__":
    pass
