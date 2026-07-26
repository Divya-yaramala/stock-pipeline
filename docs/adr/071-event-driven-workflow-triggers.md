# ADR 071 - Event-Driven Workflow Triggers

## Status

Accepted

## Context

Pipeline events needed to automatically trigger downstream actions without manual intervention.
Detecting anomalies, quality gate failures, or SLA misses is only valuable if the right
responses fire immediately.

## Decision

Built event-driven workflow with 5 trigger definitions, each mapping a pipeline event to a
list of named actions.

## Reasons

- Triggers decouple event detection from action execution
- Multiple actions per trigger (send_slack_alert + log_audit + create_report)
- Severity levels guide action selection and escalation paths
- Workflow history enables audit trail for post-incident review
- Extends event_bus.py with actionable responses rather than passive event storage

## Consequences

- All actions currently S3-based (no real execution yet)
- Trigger list must be maintained manually as new event types are added
- Future: integrate with AWS Lambda for real action execution
