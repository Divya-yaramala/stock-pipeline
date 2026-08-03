# ADR 088 - Pipeline Recovery Strategies

## Status
Accepted

## Context
Pipeline failures need structured recovery without manual intervention for every error. Without defined strategies, each failure requires an engineer to diagnose and manually restart the pipeline from scratch, adding hours of latency to daily data delivery.

## Decision
Built 5 recovery strategies (retry, skip, fallback, checkpoint, manual) with S3-based checkpointing that enables resuming from the exact failure point rather than restarting the full pipeline.

## Reasons
- 5 strategies cover all common failure modes — transient API errors (retry), non-critical steps (skip), source outages (fallback), long pipelines (checkpoint), data integrity issues (manual)
- Checkpointing enables resume from exact failure point — a 45-minute pipeline need not restart from step 1 after a step 5 failure
- Auto-recovery rate metric tracks self-healing capability — target > 80% auto-recovery without human involvement
- Manual strategy preserves human control for data integrity issues where automated recovery could corrupt downstream data
- Recovery history enables pattern detection — repeated failures in the same step signal a systemic issue requiring root cause fix

## Consequences
- Retry strategy adds latency on failure — 60-second backoff × 3 attempts = up to 3 minutes added
- Checkpoint storage adds S3 cost — mitigated by short retention (24 hours)
- Future: integrate with Airflow for automated retry execution using Airflow's built-in retry mechanism
