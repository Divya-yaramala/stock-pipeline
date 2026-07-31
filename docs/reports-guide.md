# Reports Guide — Stock Pipeline

## Overview
The pipeline generates 3 types of reports for different audiences.

## Executive Summary (Daily)
Audience: Business stakeholders, management
Format: HTML (email-ready)
Location: S3 reports/executive/YYYY/MM/DD/summary.html

Contents:
- Pipeline status: HEALTHY / DEGRADED / FAILED
- Data quality grade: A / B / C / D / F
- Total tickers processed: 5
- Anomalies detected today: X
- Predictions generated: 5
- SLA compliance: X%
- Key insights: top 3 notable findings

## Technical Report (Daily)
Audience: Data engineers, ML team
Format: JSON + HTML
Location: S3 reports/technical/YYYY/MM/DD/report.json

Contents:
- Test results (652 passing)
- CI/CD status (green/red)
- Module count (101 modules)
- Performance benchmarks
- Bottleneck analysis
- Error rates and DLQ count
- Resource usage (CPU, memory, disk)

## Weekly Digest (Every Monday)
Audience: All teams
Format: HTML
Location: S3 reports/weekly/YYYY-WW/digest.html

Contents:
- 7-day quality trend
- Total anomalies this week
- SLA compliance trend
- Top performing tickers
- Worst performing days
- Upcoming risks (from predictive alerter)

## Generating Reports
```python
# Daily reports
python -c "from ingestion.pipeline_report_generator import run_report_generation; import os; print(run_report_generation(os.getenv('AWS_BUCKET_NAME')))"

# Weekly digest (Mondays)
python -c "from ingestion.pipeline_report_generator import generate_weekly_digest; import os, datetime; print(generate_weekly_digest(os.getenv('AWS_BUCKET_NAME'), datetime.datetime.now().strftime('%Y-W%V')))"
```
