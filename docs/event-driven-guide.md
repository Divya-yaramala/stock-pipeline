# Event-Driven Architecture Guide — Stock Pipeline

## Overview
The pipeline uses event-driven workflows to automatically
trigger actions when pipeline events occur.

## Workflow Triggers

| Trigger | Event | Severity | Actions |
|---|---|---|---|
| T001 | anomaly_detected | HIGH | Slack alert + report + audit |
| T002 | quality_gate_blocked | CRITICAL | Slack + remediation + pause |
| T003 | model_drift_detected | MEDIUM | Retraining job + Slack + audit |
| T004 | sla_missed | HIGH | Slack alert + audit + escalate |
| T005 | pipeline_completed | LOW | Dashboard + summary + audit |

## Action Types

| Action | Description |
|---|---|
| send_slack_alert | Color-coded Slack notification |
| log_audit | Save to S3 audit trail |
| create_report | Save event report to S3 |
| trigger_remediation | Create auto-remediation job |
| pause_pipeline | Save pause flag to S3 |
| update_dashboard | Save dashboard refresh flag |
| send_daily_summary | Queue daily summary message |
| create_retraining_job | Queue ML model retraining |
| escalate | Save escalation record |

## Notification Channels

| Channel | When Used | Config |
|---|---|---|
| Slack | MEDIUM+ severity | SLACK_WEBHOOK_URL env var |
| Email | Daily reports | SMTP env vars |
| S3 Log | All notifications | Always active |

## Event Flow
```
Pipeline event occurs
      ↓
process_event(event_type, payload)
      ↓
find_matching_triggers() → [T001, T002...]
      ↓
For each trigger:
  execute_workflow_action(action, payload)
      ↓
save_workflow_log() → S3 workflows/logs/
```

## Severity Escalation
```
LOW    → S3 log only
MEDIUM → S3 log + Slack
HIGH   → S3 log + Slack + escalate
CRITICAL → ALL channels + pause pipeline
```

## Example: Anomaly Detected Flow
1. anomaly_detector.py detects SPIKE in AAPL
2. Publishes event: process_event("anomaly_detected", {"ticker": "AAPL", "label": "SPIKE"})
3. T001 trigger fires:
   - send_slack_alert → 🚨 red Slack message
   - create_report → S3 report saved
   - log_audit → audit trail updated
4. save_workflow_log → workflow history saved
