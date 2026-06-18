# ADR 015 - S3 Caching vs Redis

## Status

Accepted

## Context

Expensive API calls (yfinance, OpenAI) and computations (correlation matrices, feature engineering) are repeated across pipeline runs. A caching layer was needed to avoid redundant work and reduce API costs.

## Decision

Build S3-based caching in `ingestion/cache_manager.py` instead of standing up a Redis instance. Cache entries are stored as JSON objects at `cache/CACHE_KEY.json` with TTL metadata, and a decorator wraps any function with transparent cache-aside logic.

## Reasons

- **No additional infrastructure needed**: Redis requires a running server, Docker service, and connection management. S3 is already provisioned and used for all pipeline storage.
- **S3 already used for all storage**: Keeping all persistence in one place (S3) simplifies operations — no second data store to monitor, back up, or secure.
- **TTL implemented via metadata**: Expiry is stored as an ISO timestamp inside the JSON payload. `get_from_cache` checks `expires_at` on every read, making TTL enforcement stateless.
- **Persistent across restarts unlike in-memory cache**: S3 cache survives process restarts, container redeploys, and scheduler reboots — a key advantage over in-process caches like `functools.lru_cache`.
- **Free within S3 storage costs**: Cache entries are small JSON files; the marginal cost is negligible compared to provisioning and operating a Redis cluster.

## Consequences

- **Higher latency than Redis (S3 ~50ms vs Redis ~1ms)**: S3 GET requests add ~50ms per cache hit, making this unsuitable for request-path caching where sub-millisecond response is required.
- **Not suitable for sub-millisecond caching needs**: Real-time WebSocket price broadcasts or high-frequency trading signals cannot tolerate S3 cache latency.
- **Future improvement: add Redis for hot data**: A hybrid approach — Redis for frequently accessed hot data, S3 for expensive but infrequently needed computations — would cover both use cases.
