# ADR 072 - Multi-Channel Notification System

## Status

Accepted

## Context

Different stakeholders need different notification formats. Engineers need real-time
alerts to act quickly; managers need daily digests; compliance teams need a permanent
audit trail regardless of other channel availability.

## Decision

Built 3-channel notification system (Slack, email, S3 log) with severity-based routing
and simultaneous delivery for critical alerts.

## Reasons

- Slack for engineers (real-time alerts on anomalies and failures)
- Email for managers (daily reports and summaries)
- S3 log for compliance (permanent audit trail)
- Critical alerts go to ALL channels simultaneously to ensure delivery
- Graceful fallback if a channel fails — other channels still fire

## Consequences

- Each channel requires separate configuration (SLACK_WEBHOOK_URL, SMTP env vars)
- S3 log always works even if Slack/email are down
- Future: add PagerDuty for on-call escalation
