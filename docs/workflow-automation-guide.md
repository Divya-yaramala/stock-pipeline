# Workflow Automation Guide — Stock Pipeline

## Overview
The pipeline includes 5 automated workflows covering
daily, weekly, monthly, continuous, and ad-hoc patterns.

## Automated Workflows

### AW001 — Daily Market Data Refresh
Schedule: 0 6 * * 1-5 (Mon-Fri at 6 AM)
Priority: 1 (highest)
Steps:
1. fetch_stocks — Yahoo Finance API
2. validate — 8-rule validation suite
3. anomaly_detect — Isolation Forest
4. predict — Prophet + Ensemble
5. insights — GPT-3.5 summaries
6. snowflake_sync — Warehouse sync

### AW002 — Weekly Model Evaluation
Schedule: 0 8 * * 1 (Monday at 8 AM)
Priority: 2
Steps:
1. load_actuals — Load actual prices
2. calculate_accuracy — MAE, RMSE, MAPE
3. check_drift — PSI-based drift detection
4. update_registry — Model registry update

### AW003 — Monthly Compliance Report
Schedule: 0 9 1 * * (1st of month at 9 AM)
Priority: 3 (lowest)
Steps:
1. run_compliance — 4 framework checks
2. generate_certificates — Auto-certification
3. send_report — Email to stakeholders

### AW004 — Continuous Quality Monitor
Schedule: */15 * * * * (Every 15 minutes)
Priority: 1 (highest)
Steps:
1. check_freshness — Data freshness check
2. check_quality_gates — 5 quality gates
3. send_alerts — Slack alerts if issues

### AW005 — Ad-Hoc Backfill
Schedule: manual (triggered on demand)
Priority: 2
Steps:
1. detect_gaps — Find missing dates
2. backfill_data — CoinGecko/Yahoo historical
3. validate_backfill — 8-rule validation

## Recovery Strategies

| Strategy | When to Use | Action |
|---|---|---|
| retry | Transient failures (API timeout) | Retry up to 3 times |
| skip | Non-critical step failure | Skip and continue |
| fallback | Primary source unavailable | Use backup data |
| checkpoint | Long-running pipeline failure | Resume from last checkpoint |
| manual | Data integrity issues | Pause for human review |

## Workflow Reliability Targets
| Metric | Target |
|---|---|
| Success rate | > 95% |
| Avg duration AW001 | < 45 minutes |
| Auto-recovery rate | > 80% |
| Manual interventions | < 2 per week |
