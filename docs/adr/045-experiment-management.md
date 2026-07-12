# ADR 045 - Experiment Management Framework

## Status
Accepted

## Context
The pipeline already had an A/B tester (`ab_tester.py`) for model comparison, but it was
limited to exactly two variants and tightly coupled to model-selection logic. As the ML layer
grew, the team needed a more flexible framework to run controlled experiments across any
pipeline feature — not just models — with more than two variants and with explicit lifecycle
management (create → run → analyze → conclude).

## Decision
Built a separate experiment manager (`ingestion/experiment_manager.py`) that handles
multi-variant experiments independently from the existing A/B tester. Experiments are
configured in S3 (`experiments/EXPERIMENT_ID/config.json`) and outcomes are recorded per
ticker per run (`experiments/EXPERIMENT_ID/outcomes/ticker_timestamp.json`).

## Reasons
- **Multiple variants**: supports A/B/C/D — not limited to two; useful for comparing Prophet,
  Ensemble, ARIMA, and Linear models simultaneously
- **Hash-based assignment**: `MD5(experiment_id + ticker)` guarantees the same ticker always
  gets the same variant for the lifetime of the experiment, eliminating assignment noise
- **Outcomes per ticker**: records metric name + value per ticker, allowing per-stock analysis
  in addition to aggregate winner determination
- **Explicit lifecycle**: create → record outcomes → analyze → conclude; status field prevents
  accidentally re-running concluded experiments
- **Complementary to feature flags**: a flag gates whether a feature runs at all; an experiment
  determines which variant of a feature runs — both are needed in a production ML pipeline

## Consequences
- Experiments must be manually concluded — no auto-expiry; add TTL check in future
- Winner is determined by highest average metric — higher-is-better assumption; document when
  lower-is-better metrics (e.g. error rate) are used
- No statistical significance testing (p-value) yet — winner label is directional only
- Future: add sample-size guardrails and p-value calculation for rigorous conclusions
