# ADR 041 - HTML Health Dashboard

## Status
Accepted

## Context
As the pipeline grew to cover 5 tickers with ML, anomaly detection, quality gates, and
auto remediation, stakeholders needed a single-glance view of pipeline health without logging
into Airflow, CloudWatch, or any monitoring tool. We needed a shareable health report that
required no additional infrastructure.

## Decision
Built an HTML health dashboard in `ingestion/pipeline_health_dashboard.py` that generates a
self-contained HTML file saved to S3:

- **Pipeline Summary section**: 7 KPI tiles (total tickers, successful, failed, avg quality,
  anomalies, predictions, duration)
- **Ticker Status table**: color-coded rows (green=success, yellow=warning, red=failed)
- **System Health section**: badge showing healthy/warning/critical with numeric score
- Saved to `reports/health_dashboard/YYYY/MM/DD/dashboard.html`

## Reasons
- **No web server required**: S3 static hosting can serve the HTML directly
- **Shareable via URL**: a single S3 presigned URL gives stakeholders instant access
- **Email-compatible**: HTML renders inline in any email client for daily digests
- **Color-coded status**: green/yellow/red rows surface problems in under 5 seconds
- **Zero additional infrastructure**: uses only boto3 + stdlib; no React, no Flask

## Consequences
- Dashboard is static — must be regenerated each time new data arrives
- No drill-down or interactivity; for deep dives, Airflow logs or raw S3 data is needed
- S3 static website hosting requires public bucket or presigned URLs for sharing
- Future: add auto-refresh meta tag and host on S3 static website for live updates
