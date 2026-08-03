# ADR 086 - Data Contract Enforcement Pattern

## Status
Accepted

## Context
Data contracts were advisory — they documented expected schemas but did not actively block non-conforming data. Without enforcement, contract violations silently passed through the pipeline, corrupting downstream tables and ML model inputs.

## Decision
Built a contract enforcer that blocks pipeline on violations, logs violations to S3 with a 7-day history, and computes a single health score per contract.

## Reasons
- Blocking prevents downstream corruption — it is easier to reject bad records at ingestion than to backfill after corruption
- Violation history tracks contract health over time — repeated violations signal upstream source changes
- Health score (100 - violation_rate) is a single metric that fits on a dashboard without needing to parse raw violation logs
- DLQ pattern handles blocked records gracefully — they are not lost, just quarantined for manual review
- Complements pipeline_validator with contract-level checks — validator checks statistical rules, enforcer checks schema conformance

## Consequences
- Strict enforcement may block edge case valid data (e.g., trading halts with zero volume)
- Blocked records go to DLQ for manual review before re-ingestion
- Future: add auto-remediation for common violations (e.g., type coercion for string prices)
