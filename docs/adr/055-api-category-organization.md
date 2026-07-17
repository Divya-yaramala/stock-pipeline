# ADR 055 — API Endpoint Category Organization

## Status
Accepted

## Context
The REST API grew from 7 endpoints (Day 26) to 13 endpoints (Day 68) across diverse pipeline domains: ML inference, AI summarization, NLP sentiment, data governance, observability, and security. Without a taxonomy, consumers cannot discover endpoints by concern — they must read the full endpoint list to find what they need.

## Decision
Organize all 13 endpoints into 9 named categories that map to pipeline layers:

| Category | Endpoints |
|---|---|
| system | /health, /feature-flags |
| market_data | /prices/{ticker}, /summary/{ticker} |
| ml | /anomalies/{ticker}, /predictions/{ticker} |
| ai | /insights/{ticker} |
| nlp | /sentiment/{ticker} |
| quality | /quality-gates/{ticker} |
| governance | /data-products |
| observability | /events/summary, /pipeline-health |
| security | /privacy-scan/{prefix} |

Categories are exposed programmatically via `/api-docs/endpoints/{category}` and stored as the `category` field in `API_ENDPOINTS` in `api/api_docs.py`.

## Reasons
1. **Pipeline layer mapping**: categories align with how the pipeline is built — categories like `ml`, `nlp`, `governance` map directly to modules and ADRs
2. **Self-documenting**: `/api-docs/endpoints/{category}` replaces static docs that drift out of date
3. **Discoverability**: consumer can query `/api-docs/summary` to see all categories, then drill into one
4. **FastAPI-native**: Swagger UI at `/docs` can be extended with FastAPI `tags` to mirror these categories
5. **9 categories covers all current domains** — no catch-all "other" needed

## Consequences
- Category names must remain stable — renaming breaks consumer scripts that call `/api-docs/endpoints/{category}`
- Some endpoints (e.g. `/health`) span concerns but are assigned to the most natural category
- Future: add `tags=[category]` to FastAPI route decorators so Swagger UI groups endpoints by category automatically
