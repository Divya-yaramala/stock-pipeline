# ADR 027 - Model Drift Detection with PSI

## Status
Accepted

## Context
Needed automated detection of when ML models become stale. Without drift monitoring, models
silently degrade as market conditions change, producing increasingly unreliable predictions
without any alerting.

## Decision
Built PSI-based drift detection with automatic retraining triggers. Feature distributions are
compared against stored baselines using Population Stability Index. Time-based schedule
fallback ensures models are refreshed even when drift signals are quiet.

## Reasons
- PSI is industry-standard metric for distribution shift
- Threshold-based severity (none/moderate/significant) is interpretable
- Combines feature drift and prediction drift signals
- Automatic retraining jobs reduce manual monitoring burden
- Time-based fallback (30 days) catches silent degradation

## Consequences
- PSI calculation requires baseline distribution storage
- False positives possible with small sample sizes
- Retraining jobs still require manual execution (no auto-trigger pipeline yet)
