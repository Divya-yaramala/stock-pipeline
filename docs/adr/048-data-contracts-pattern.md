# ADR 048 - Data Contracts Pattern

## Status

Accepted

## Context

As the pipeline grew to serve multiple consumers (trading, risk, analytics, executives), there was no formal agreement on what each data producer was obligated to deliver. Consumers had no way to detect upstream schema changes before they broke their pipelines. A formal contract mechanism was needed to define schema, SLA, and quality expectations between producers and consumers.

## Decision

Built a data contract manager (`ingestion/data_contract_manager.py`) with schema validation and backward compatibility checks. Contracts are versioned JSON documents stored in S3 under `data_contracts/<contract_id>/<version>.json`.

The initial contract (`STOCK_PRICE_CONTRACT`) covers the stock price event with 7 required fields, type validation, range checks, and SLA thresholds.

## Reasons

- **Contracts define schema, SLA, and quality expectations** — producers and consumers agree on field names, types, required fields, and SLA targets in a single versioned document
- **Backward compatibility checks prevent breaking consumers** — `check_contract_compatibility` detects removed required fields and type changes before deployment
- **Version-controlled contracts in S3** — each contract version is independently retrievable, enabling rollback and audit
- **Violations logged for producer accountability** — `validate_against_contract` logs every violation so producers can track data quality against their own contracts
- **Complements data mesh ownership model** — each data product (DP001–DP005) can have its own contract owned by its domain team

## Consequences

- Contracts must be updated manually when schema changes — no auto-generation from code yet
- No automated enforcement in the pipeline today — validation is advisory
- Future: block pipeline on contract violation using the quality gate layer
- Future: generate contracts automatically from dbt schema.yml definitions
