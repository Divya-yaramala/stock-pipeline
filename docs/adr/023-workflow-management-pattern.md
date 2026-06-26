# ADR 023 - Workflow Management Pattern

## Status
Accepted

## Context
The stock pipeline grew to include multiple pipeline schedules — daily ingestion, weekly reports,
monthly backfills, and continuous Kafka streaming. Managing these as ad-hoc scripts provided no
visibility into what ran, when, or whether it succeeded. We needed a structured way to define,
trigger, and audit multiple pipeline workflows without adding new scheduler infrastructure.

## Decision
Built a custom workflow manager (`ingestion/workflow_manager.py`) with 5 predefined workflows,
a cron expression parser, and S3-based trigger history. Each workflow run is recorded as a JSON
object under `workflows/triggers/YYYY/MM/DD/` to provide a full audit trail. A companion pipeline
scheduler (`ingestion/pipeline_scheduler.py`) supports dynamic schedule creation, updates, and
next-run-time calculation.

## Reasons
- 5 predefined workflows cover all pipeline needs — daily, weekly, monthly, hourly, and continuous
- Cron expressions familiar to all engineers — no proprietary DSL to learn
- S3 trigger history provides audit trail — every execution is recorded and queryable
- No additional scheduler infrastructure needed — reuses existing S3 storage
- Continuous workflows handled separately from cron — avoids forcing a cron model onto streaming jobs

## Consequences
- Less feature-rich than Apache Airflow scheduler — no UI, retries, or dependency chaining
- No retry logic built into workflow manager — failed workflows must be re-triggered manually
- Manual schedule updates required — no live reload; changes require a code deploy
