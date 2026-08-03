# ADR 087 - Workflow Automation Engine

## Status
Accepted

## Context
Manual pipeline triggering is error-prone and not scalable. Without automation, engineers must remember to run daily refreshes, weekly model evaluations, and monthly compliance reports on schedule. A missed run causes stale data, model drift, and compliance gaps.

## Decision
Built a workflow automation engine with 5 predefined workflows covering daily, weekly, monthly, continuous, and ad-hoc execution patterns. Each workflow has a cron schedule, priority level, and ordered step list. Execution records are stored in S3 with full history.

## Reasons
- 5 workflows cover the full operational range — from 15-minute quality checks to monthly compliance reports
- Execution history enables reliability tracking — success rate and average duration surface degrading workflows before they fail
- Priority system manages resource contention — P1 workflows preempt P3 when running simultaneously
- Execution IDs enable distributed tracing across S3, Airflow, and API logs
- Reliability metrics show workflow health trends without requiring a dedicated monitoring tool

## Consequences
- Workflows are still triggered manually or via Airflow — no standalone scheduler daemon
- Cron expressions are defined but not automatically evaluated by this module
- Future: deploy as AWS EventBridge scheduled rules to replace Airflow cron operators
