# ADR 032 - A/B Testing Framework for ML Models

## Status
Accepted

## Context
With multiple ML models in production (Prophet for forecasting, Ensemble for prediction), there was
no systematic way to compare their real-world performance. Manual inspection of S3 outputs was
time-consuming and subjective. A/B testing provides a data-driven framework for deciding which
model to promote to production.

## Decision
Built a custom A/B testing framework (`ingestion/ab_tester.py`) with hash-based ticker assignment,
result recording to S3, and MAE-based winner determination. Experiments are created, run, and
concluded through Python functions rather than a third-party service.

## Reasons
- Hash-based assignment ensures consistent model per ticker — no random flicker between models
- Hash is deterministic: same ticker always sees same model, enabling fair comparison over time
- Confidence levels (low/medium/high) based on sample count prevent premature conclusions
- Winner determined by MAE — interpretable metric understood by non-ML stakeholders
- Results saved to S3 under `models/experiments/` for full audit trail
- No external dependency: avoids Optimizely, LaunchDarkly, or MLflow cost/complexity

## Consequences
- Requires manual experiment creation and explicit conclusion call
- Minimum 30 samples needed for high confidence — may take several days to accumulate
- No statistical significance testing (t-test, p-value) — future improvement opportunity
- Traffic split is per-ticker not per-request, which limits granularity for low-ticker setups
