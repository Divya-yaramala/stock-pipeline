# ADR 047 - Event-Driven Pipeline Architecture

## Status

Accepted

## Context

As pipeline stages grew in number and complexity, tight coupling between stages made it difficult to add consumers, replay events, or audit pipeline activity. A loose-coupling mechanism was needed so stages could publish outcomes without knowing who would consume them.

## Decision

Built an S3-based event bus (`ingestion/event_bus.py`) with 10 event types covering all major pipeline milestones. Events are stored as JSON in S3 under `events/YYYY/MM/DD/event_type/event_id.json`.

## Reasons

- **Events decouple producers from consumers** — anomaly detector publishes `anomaly_detected`; Slack alerter, dashboard, and trading consume it independently
- **Full audit trail of all pipeline events in S3** — every event is durable and queryable by date and type
- **Event summary enables pipeline activity dashboard** — `get_event_summary` gives a daily count per event type without scanning logs
- **10 event types cover all major pipeline milestones** — ingestion, anomaly, prediction, quality gates, SLA, retraining, completion, and failure
- **No message broker needed** — S3 as a durable event store avoids running and maintaining Kafka/SQS for portfolio-scale workloads

## Consequences

- Not real-time — S3 polling required for consumers; latency measured in seconds to minutes
- Events are not deleted automatically — a retention policy (e.g., 30 days) must be applied to the `events/` prefix
- Future: replace S3 polling with SNS/SQS for true real-time event delivery at production scale
