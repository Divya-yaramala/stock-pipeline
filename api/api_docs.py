"""API documentation module — self-describing endpoint registry."""

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter

API_ENDPOINTS: List[Dict[str, Any]] = [
    {
        "method": "GET",
        "path": "/health",
        "description": "Health check",
        "category": "system",
    },
    {
        "method": "GET",
        "path": "/prices/{ticker}",
        "description": "Latest stock prices",
        "category": "market_data",
    },
    {
        "method": "GET",
        "path": "/anomalies/{ticker}",
        "description": "Anomaly detection results",
        "category": "ml",
    },
    {
        "method": "GET",
        "path": "/predictions/{ticker}",
        "description": "5-day price predictions",
        "category": "ml",
    },
    {
        "method": "GET",
        "path": "/insights/{ticker}",
        "description": "GPT market insights",
        "category": "ai",
    },
    {
        "method": "GET",
        "path": "/sentiment/{ticker}",
        "description": "News sentiment score",
        "category": "nlp",
    },
    {
        "method": "GET",
        "path": "/summary/{ticker}",
        "description": "Combined ticker summary",
        "category": "market_data",
    },
    {
        "method": "GET",
        "path": "/quality-gates/{ticker}",
        "description": "Quality gate check",
        "category": "quality",
    },
    {
        "method": "GET",
        "path": "/feature-flags",
        "description": "All feature flags",
        "category": "system",
    },
    {
        "method": "GET",
        "path": "/data-products",
        "description": "Data mesh products",
        "category": "governance",
    },
    {
        "method": "GET",
        "path": "/events/summary",
        "description": "Event bus summary",
        "category": "observability",
    },
    {
        "method": "GET",
        "path": "/pipeline-health",
        "description": "Pipeline health score",
        "category": "observability",
    },
    {
        "method": "GET",
        "path": "/privacy-scan/{prefix}",
        "description": "PII scan results",
        "category": "security",
    },
]

router = APIRouter(prefix="/api-docs", tags=["api-docs"])


def get_api_summary() -> Dict[str, Any]:
    """Return API version, total endpoint count, and count by category."""
    by_category: Dict[str, int] = {}
    for ep in API_ENDPOINTS:
        cat: str = str(ep["category"])
        by_category[cat] = by_category.get(cat, 0) + 1
    return {
        "total_endpoints": len(API_ENDPOINTS),
        "by_category": by_category,
        "version": "2.0.0",
        "generated_at": datetime.utcnow().isoformat(),
    }


def get_endpoints_by_category(category: str) -> List[Dict[str, Any]]:
    """Return all endpoints belonging to the given category."""
    return [ep for ep in API_ENDPOINTS if str(ep["category"]) == category]


@router.get("/summary")
def api_docs_summary() -> Dict[str, Any]:
    """Return API summary with version and endpoint count by category."""
    return get_api_summary()


@router.get("/endpoints/{category}")
def api_docs_by_category(category: str) -> List[Dict[str, Any]]:
    """Return all endpoints for a specific category."""
    return get_endpoints_by_category(category)
