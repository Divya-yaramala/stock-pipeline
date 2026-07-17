# ADR 054 — API Versioning Strategy

## Status
Accepted

## Context
The REST API has grown from 7 endpoints to 13 endpoints across 6 functional categories (system, market_data, ml, ai, nlp, quality, governance, observability, security). Without a clear organization strategy, the API becomes difficult to discover and document. Consumers need to know what endpoints exist, what category they belong to, and how to find the right one.

## Decision
Organize REST API endpoints by functional category without adding URL versioning (`/v1/`, `/v2/`). Document the API version in the OpenAPI metadata and through a self-describing `/api-docs` router:

- **Category grouping**: ml, ai, nlp, quality, governance, observability, security — improves discoverability
- **API docs module** (`api/api_docs.py`): `API_ENDPOINTS` list is the single source of truth; `/api-docs/summary` returns version + count by category; `/api-docs/endpoints/{category}` filters by category
- **Current version**: `2.0.0` (added 6 new endpoints on Day 68)
- **No URL versioning**: keep URLs simple (`/quality-gates/AAPL` not `/v2/quality-gates/AAPL`)
- **FastAPI Swagger UI**: auto-generated at `/docs` — always up to date

## Reasons
1. **Self-documenting**: `/api-docs/summary` endpoint lets consumers query the API about itself rather than reading a static file
2. **Simple URLs**: URL versioning adds friction for consumers and is unnecessary while we control all clients
3. **Category organization**: grouping by ml/ai/nlp/quality makes the API navigable as it grows beyond 13 endpoints
4. **FastAPI native**: Swagger UI at `/docs` already provides documentation — the `api_docs` module adds a programmatic interface

## Consequences
- No formal backward compatibility guarantees until a breaking change requires `/v2/` prefix
- Swagger UI at `/docs` is already the primary documentation surface — `/api-docs` supplements it
- Adding a new endpoint requires updating `API_ENDPOINTS` in `api_docs.py` — one source of truth
- Future: add `/v1/` prefix when a breaking change is introduced; maintain old routes for one release cycle
