# ADR 033 - Slack Alerting Integration

## Status
Accepted

## Context
The pipeline runs unattended overnight, but anomalies, quality failures, and pipeline errors were
only discoverable by inspecting S3 logs or the Airflow UI. Engineers needed real-time visibility
without polling a dashboard — a push notification to an existing collaboration tool was the lowest
friction solution.

## Decision
Built a Slack webhook integration (`ingestion/slack_alerter.py`) with color-coded severity levels
(green/yellow/red), typed alert functions for each event type, and a daily pipeline summary. Alerts
are wired into `anomaly_detector.py`, `quality_reporter.py`, and the Airflow DAG's final task.

## Reasons
- Slack webhooks are simple, reliable, and require no SDK or authentication beyond the URL
- Color coding (good/warning/danger) makes severity immediately visible in the message feed
- Graceful fallback: if `SLACK_WEBHOOK_URL` is not set, all functions return False silently
- Every alert call is wrapped in try/except — Slack failure never breaks the pipeline
- Daily summary via `TriggerRule.ALL_DONE` runs even if upstream tasks fail
- Alert functions are individually testable without a real Slack workspace

## Consequences
- Requires a Slack workspace and an Incoming Webhook app to use
- Webhook URL must be stored in `.env` and never committed to version control
- Free Slack plan has a 10k message history limit — not a concern for a 20-call/day pipeline
- One Slack alert per anomalous ticker per day — could generate noise on high-volatility days
