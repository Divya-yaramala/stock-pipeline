# ADR 050 - Data Privacy and PII Management

## Status

Accepted

## Context

Financial data pipelines must handle PII carefully for compliance with GDPR, CCPA, and internal data governance policies. Although stock price data itself (OHLCV) contains no PII, audit logs, error records, and user-generated inputs could accidentally include personal information. A systematic approach to PII detection, masking, and anonymization was needed.

## Decision

Built a two-module privacy layer:
- `ingestion/pii_detector.py` — regex-based PII scanner covering 5 pattern types with risk scoring and masking
- `ingestion/data_privacy_manager.py` — 4 privacy policies covering retention, classification, and PII rules

## Reasons

- **Stock data itself has no PII but audit logs might** — `run_pii_scan` can scan any S3 prefix including `errors/` and `audit/` to catch accidental PII leakage
- **PII scanner catches accidental PII in pipeline outputs** — 5 patterns (email, phone, SSN, credit card, IP) cover the most common PII types without requiring ML models
- **Privacy policies enforce retention and encryption requirements** — 4 policies map to the 4 pipeline data domains, each with explicit retention days and classification
- **Anonymization supports safe data sharing** — `anonymize_dataset` SHA256-hashes specified fields so anonymized data can be shared with external teams
- **SHA256 hashing is irreversible** — re-identification is not possible from the hash alone, making it suitable for analytics without exposing original values

## Consequences

- PII scan adds S3 API latency proportional to file count in the scanned prefix
- Masking must be reversible for legitimate access — masked data cannot be unmasked without the original; for access needs, use role-based S3 bucket policies instead
- Future: integrate with AWS Macie for automated ML-based PII detection at scale
