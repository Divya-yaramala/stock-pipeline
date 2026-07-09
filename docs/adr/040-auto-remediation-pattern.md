# ADR 040 - Auto Remediation Pattern

## Status
Accepted

## Context
Manual intervention for every pipeline issue is not scalable. As the pipeline grows to cover 5
tickers across multiple daily stages, each failure requiring human diagnosis and re-trigger
creates unacceptable operational overhead. We needed a system that detects common failure patterns
and initiates recovery automatically.

## Decision
Built an auto remediation system in `ingestion/auto_remediation.py` that detects 5 issue types
from pipeline metrics and creates remediation job records in S3 for each detected problem.
The system is decoupled into detection (immediate, automatic) and execution (deferred, auditable).

## Reasons
- **5 issue types** cover the most common pipeline failures: stale data, missing files, low
  quality score, high anomaly rate, and prediction failure
- **Remediation jobs in S3**: each triggered job is saved to `remediation/YYYY/MM/DD/` for
  a complete audit trail
- **Decoupled from execution**: jobs are created but not automatically executed, allowing
  human review before action — important when remediation could have side effects
- **History tracking**: `get_remediation_history()` surfaces recurring issues over 7 days,
  enabling proactive threshold tuning
- **No external dependencies**: uses only boto3 (already required) and stdlib

## Consequences
- Remediation jobs are currently created but not executed automatically — human review required
- Recurring issues will accumulate records without resolution if execution is not wired up
- Future: integrate with Airflow REST API to auto-trigger remediation DAG runs, turning
  detection into self-healing
