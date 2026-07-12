# ADR 044 - Feature Flags Pattern

## Status
Accepted

## Context
As the pipeline grew to include optional features (Kafka streaming, chaos engineering, A/B
testing), the team needed a way to enable or disable individual capabilities without modifying
code or redeploying. Hardcoding feature availability led to accidental activations — chaos
scenarios ran in environments where they were not intended, and Kafka calls failed in
environments without a broker.

## Decision
Built an S3-based feature flag manager (`ingestion/feature_flag_manager.py`) with 10 default
flags. Flags are stored at `feature_flags/flags.json` in S3 and merged with in-code defaults
on every read, so the system always has a known baseline even without S3 access.

Default flags:

| Flag | Default | Rationale |
|---|---|---|
| enable_gpt_insights | True | Core AI feature, on by default |
| enable_kafka_streaming | False | Requires broker; off until provisioned |
| enable_chaos_engineering | False | Must be explicitly opted in |
| enable_ensemble_models | True | Better predictions; on by default |
| enable_news_sentiment | True | Adds value with no risk |
| enable_slack_alerts | True | Critical for ops awareness |
| enable_email_reports | True | Stakeholder reporting |
| enable_snowflake_sync | True | Core warehouse path |
| enable_auto_remediation | True | Safe to run automatically |
| enable_ab_testing | False | Opt-in experimentation |

## Reasons
- **Toggle without redeployment**: operators change a JSON file in S3, pipeline picks it up
  on next run
- **Safe rollout**: new features default to `False`; enable them for a subset of environments
  before going wide
- **Chaos engineering gated**: `enable_chaos_engineering: False` ensures failure injection
  never runs accidentally in production
- **Kafka optional**: not all environments provision a broker; flag lets the pipeline run
  without it
- **S3 persistence**: flags survive restarts and are visible to all pipeline workers

## Consequences
- S3 read on every `is_enabled()` call — acceptable for batch pipelines; add an in-memory
  cache (TTL 60 s) if called frequently in a streaming context
- Flags must be manually managed — no UI; operators edit JSON directly or use CLI helpers
- `run_flag_audit()` provides visibility into which flags differ from defaults
- Future: migrate to AWS AppConfig for real-time flag pushes without S3 polling
