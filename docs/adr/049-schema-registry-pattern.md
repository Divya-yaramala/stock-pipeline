# ADR 049 - Schema Registry Pattern

## Status

Accepted

## Context

As the number of datasets grew (prices, anomalies, predictions, sentiment), there was no central place to look up what each dataset's schema looked like, what version it was on, or whether a proposed change was safe. Consumers were discovering schema changes at runtime instead of at deployment time.

## Decision

Built an S3-based schema registry (`ingestion/schema_registry.py`) that stores versioned schema definitions as JSON under `schema_registry/<schema_name>/<version>.json`. A `validate_schema_evolution` function checks whether a proposed change is safe (adding optional fields) or breaking (removing fields, changing types) before any migration proceeds.

## Reasons

- **Single source of truth for all schemas** — 4 schemas registered at startup; any module can query the registry instead of hardcoding expectations
- **Version history enables rollback to previous schema** — each version is an independent S3 object; reverting to v1.0.0 is a single read
- **Evolution validation prevents accidental breaking changes** — `validate_schema_evolution` classifies every change as safe or breaking before deployment
- **Complements data contracts with technical schema details** — contracts define SLA and ownership; the registry stores the technical field definitions
- **No additional infrastructure needed** — S3 is already used throughout the pipeline; no Confluent Schema Registry or Kafka dependency required

## Consequences

- Schema lookup adds one S3 API call per validation — acceptable at portfolio scale, would benefit from in-memory caching at production scale
- Manual schema registration required — schemas must be registered explicitly via `run_schema_registry_setup`
- Future: auto-generate schemas from dbt `schema.yml` to keep registry in sync with warehouse definitions
