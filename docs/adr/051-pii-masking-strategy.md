# ADR 051 - PII Masking Strategy

## Status

Accepted

## Context

When PII is found in pipeline data, it must be masked before the data can be logged, shared, or moved to less-restricted storage. The masking approach needs to be consistent, debuggable, and irreversible to prevent re-identification while preserving enough data shape for operational use.

## Decision

Implemented pattern-based masking in `ingestion/pii_detector.py` that preserves the structural shape of PII values while hiding the sensitive content:
- email → `u***@***.com` (first char + masked local + masked domain + real TLD)
- phone → `***-***-XXXX` (last 4 digits visible)
- SSN → `***-**-XXXX` (last 4 digits visible)
- credit card / IP → fixed-length `*` blocks

## Reasons

- **email → u***@***.com preserves domain structure** — operators can confirm the field is an email and identify the TLD for debugging without seeing the actual address
- **phone → ***-***-XXXX keeps last 4 digits** — consistent with industry practice (bank statements, support tickets) and allows partial matching with known records
- **ssn → ***-**-XXXX keeps last 4 digits** — same industry-standard convention used by the IRS and financial institutions
- **Shape preservation helps debugging without exposing PII** — a masked value is clearly distinguishable from a non-PII value in logs, making it easy to confirm masking worked
- **Regex patterns catch most common PII formats** — 5 patterns cover the realistic PII surface area for a financial pipeline without requiring ML models or paid services

## Consequences

- Custom regex may miss uncommon PII formats (e.g. international phone numbers, non-US SSNs) — acceptable for a US-focused stock pipeline
- Masking is not reversible — if original data is needed for legitimate purposes, use role-based access to the unmasked S3 source; never try to reverse a masked value
- Future: integrate with AWS Macie for ML-based PII detection covering formats the regex patterns miss
