# ADR 077 - Predictive Monitoring Pattern

## Status
Accepted

## Context
Reactive alerting fires only after a metric has already breached a threshold, meaning issues are detected too late to intervene. By the time an anomaly alert fires, data quality may already be degraded, an SLA may already be missed, and root cause investigation must happen under pressure.

## Decision
Built a predictive alerter using trend analysis and Z-score probabilities to forecast issues before they become critical. Paired with an intelligent monitor that uses metric correlations to generate root cause hypotheses and health fingerprints to detect silent state changes.

## Reasons
- Sigmoid function maps Z-score to an interpretable probability (0–1) that non-technical stakeholders can act on
- Quality degradation trend predicts the number of days until a threshold breach, enabling proactive remediation
- SLA risk prediction based on completion time trends enables intervention before a pipeline run is late
- Root cause hypotheses generated from metric correlations speed up incident resolution by surfacing likely causes immediately
- Health fingerprints (MD5 of metric values) detect silent state changes where no individual metric crosses a threshold but the overall system state has shifted

## Consequences
- Predictions may have false positives — a downward trend may reverse naturally
- Trend-based predictions require sufficient history (7+ days) to be statistically meaningful
- Sigmoid-based anomaly probability may miss slow, gradual drifts that never produce a large Z-score
- Future: replace linear trend extrapolation with LSTM for more accurate time series prediction
