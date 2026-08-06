# ADR 094 - Service Level Objectives Framework

## Status
Accepted

## Context
Needed measurable reliability targets beyond SLA deadlines. The existing SLA monitor tracked whether pipeline steps completed on time, but had no way to express multi-dimensional reliability goals covering data quality, prediction accuracy, and API responsiveness in a single framework.

## Decision
Defined 5 SLOs covering availability, freshness, quality, accuracy, and latency. Each SLO has a named metric key mapped to the observability metrics dict, enabling automated compliance checking with each pipeline run.

## Reasons
- SLOs are more granular than binary SLA pass/fail — compliance percentage enables trend tracking over days and weeks
- 5 SLOs cover all customer-facing pipeline aspects — availability, freshness, quality, accuracy, latency
- Compliance percentage enables trend tracking — dropping from 5/5 to 4/5 is an early warning signal
- Golden signals provide standardized SRE metrics — latency/traffic/errors/saturation align with industry standard
- Error budget concept enables informed risk decisions — knowing remaining budget before a freeze

## Consequences
- SLO targets require tuning based on historical performance — initial targets are conservative estimates
- API latency SLO requires actual latency measurement — currently using proxy metrics
- Future: implement error budget tracking and alerting when budget drops below 20%
