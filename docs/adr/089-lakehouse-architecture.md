# ADR 089 - Data Lakehouse with Bronze/Silver/Gold Layers

## Status
Accepted

## Context
Flat S3 prefixes (raw/, processed/, errors/) lack structure for different data quality levels. Raw data mixed with validated data makes it impossible to reprocess from source or serve different consumers with appropriate quality guarantees.

## Decision
Implemented the medallion architecture (bronze/silver/gold) with three distinct S3 layers. Each layer has a clear purpose, quality gate, and retention policy. Data flows one-way: raw → validated → aggregated.

## Reasons
- Bronze: preserves raw data exactly as received — enables full reprocessing when validation rules change
- Silver: validated clean data (quality score >= 80%) for ML training and analytics — prevents bad data from reaching models
- Gold: pre-aggregated business metrics for dashboards — sub-second queries without recomputing from raw
- Clear data lineage from source to business value — every record_id traces back to its bronze origin
- Retention tiers match data value: bronze 365 days, silver 730 days, gold 1825 days (5 years)

## Consequences
- 3x storage cost vs single layer (bronze + silver + gold for every record)
- Pipeline must write to all 3 layers per run — adds latency
- Validation gate at bronze→silver may drop records that should be investigated
- Future: add platinum layer for ML feature store with pre-computed features per ticker
