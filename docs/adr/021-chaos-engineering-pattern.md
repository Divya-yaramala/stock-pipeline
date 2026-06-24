# ADR 021 - Chaos Engineering Pattern

## Status
Accepted

## Context
The stock pipeline runs multiple external integrations (S3, yfinance API, Postgres, Snowflake) and
needs to be resilient to partial failures. Without controlled failure testing, weaknesses only surface
in production — often during high-stakes periods. We needed a way to simulate failure conditions in a
safe, repeatable, and auditable manner.

## Decision
Built a chaos engineering module (`ingestion/chaos_engineer.py`) with probability-based fault injection
across five failure scenarios. Chaos injection is disabled by default and only activated via the
`CHAOS_ENABLED=true` environment variable. All injected events are saved to S3 for audit trail review.

## Reasons
- Netflix pioneered this pattern with Chaos Monkey — it is now an industry standard for resilience testing
- Finding weaknesses before production failures do is far cheaper than incident response
- Controlled by `CHAOS_ENABLED` env var — safe by default, impossible to accidentally enable
- 5 scenarios cover the most common failure modes: S3 latency, API timeout, data corruption, partial ticker failure, network partition
- Results saved to S3 under `chaos/YYYY/MM/DD/` for full audit trail and trend analysis

## Consequences
- Must never enable `CHAOS_ENABLED=true` in production without a written rollback plan and monitoring in place
- Adds conditional branches to pipeline code — every chaos injection point must be explicitly tested
- Requires active monitoring to distinguish injected failures from real failures in dashboards
