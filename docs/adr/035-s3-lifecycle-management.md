# ADR 035 - S3 Lifecycle Management

## Status
Accepted

## Context
As the pipeline runs daily it accumulates raw and processed data in S3 indefinitely. Without
a retention strategy, storage costs grow linearly with pipeline age. Different data types have
different business value over time — raw OHLCV data is valuable for 90 days, sentiment scores
only for 30 days, cache objects for 7 days.

## Decision
Implement a Python-based S3 lifecycle manager (`s3_optimizer.py`) with per-prefix retention
policies, dry-run mode, batch deletion (1 000 objects/request), and optional Glacier archival.
Run it as a weekly Airflow task rather than using native S3 lifecycle rules.

## Reasons
- Per-prefix retention policies are more granular than native S3 lifecycle rules allow by default
- Dry-run mode lets engineers preview what will be deleted before committing — reduces risk
- Batch delete (1 000 objects/request) minimises API call costs for large prefixes
- Glacier archival (move_to_glacier) preserves data at $0.004/GB instead of deleting it
- Python implementation keeps the logic version-controlled and testable alongside the pipeline
- Cost savings are calculated and stored in reports/ so stakeholders can track ROI

## Consequences
- Native S3 lifecycle rules are NOT configured — the Python task must run on schedule
- If Airflow is down for an extended period, objects will not be expired automatically
- Dry-run default (dry_run=True) means production deletions require an explicit flag flip
- Glacier-archived objects incur retrieval fees if accessed again — acceptable for cold data
- Future: evaluate AWS S3 Intelligent-Tiering for automatic cost optimisation
