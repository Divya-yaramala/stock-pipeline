# ADR 028 - Data Lineage Tracking

## Status
Accepted

## Context
As the pipeline grew to cover ingestion, validation, ML inference, and serving layers, we needed
visibility into how data flows between datasets and which downstream systems are affected when an
upstream source changes. Without lineage tracking, diagnosing data quality incidents or estimating
the blast radius of schema changes required manual tracing across multiple modules.

## Decision
Built a custom lineage tracker using S3-based storage. Each pipeline step records a lineage event
capturing the source dataset, target dataset, transformation name, ticker, and timestamp. An impact
analyzer sits on top to answer questions like "which datasets break if raw_prices schema changes?"

## Reasons
- Records upstream and downstream relationships per dataset, enabling full graph traversal
- Impact analysis helps prioritize incident response by surfacing severity (low/medium/high)
- Full data flow trace from source to serving layer (Yahoo Finance → raw → validated → marts)
- No additional infrastructure required — S3 is already the central store for all pipeline artifacts
- Schema change impact severity (< 3 = low, < 7 = medium, 7+ = high) guides engineering effort

## Consequences
- Lineage must be manually instrumented at each pipeline step; it is not automatic
- No real-time lineage graph visualization — records are JSON files queried on demand
- Future: integrate with Apache Atlas or DataHub for a managed lineage graph with UI
