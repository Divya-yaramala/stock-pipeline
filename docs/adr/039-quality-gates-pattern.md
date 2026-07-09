# ADR 039 - Quality Gates Pattern

## Status
Accepted

## Context
As the pipeline grew to cover ingestion, anomaly detection, forecasting, and reporting, bad data
could silently propagate through every stage. A single stale or incomplete dataset would corrupt
downstream Snowflake models, mislead ML predictions, and generate incorrect alerts. We needed
automated checkpoints to catch data quality failures before they cascaded.

## Decision
Built a quality gate system in `ingestion/quality_gate.py` with five configurable gates and a
companion auto-remediation module in `ingestion/auto_remediation.py`:

- **5 gates** covering freshness, completeness, quality score, anomaly rate, and prediction accuracy
- **Two action tiers**: `block` halts downstream processing; `warn` logs but allows continuation
- **Gate history**: results saved to S3 `quality_gates/YYYY/MM/DD/` for 7-day trend analysis
- **Auto remediation**: 5 issue types mapped to remediation actions, triggered on gate failures

## Reasons
- **Fail-fast**: block gates prevent downstream corruption at the source
- **Graceful degradation**: warn gates surface issues without halting the pipeline unnecessarily
- **Auditability**: every gate result is written to S3 with timestamp and metric values
- **Trend visibility**: gate history enables alerting on repeated failures over days
- **Auto recovery**: remediation records create a traceable action log for each detected issue

## Consequences
- Overly tight thresholds may block valid data during market volatility — requires tuning
- Gate history grows ~5 tickers × 365 days = 1,825 S3 objects/year (negligible cost)
- Remediation records are currently logged only — execution of fixes still requires manual action
- Future: wire remediation actions to actual pipeline re-triggers via Airflow API calls
