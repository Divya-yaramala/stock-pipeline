# ADR 009 - HTML Reports with Jinja2

## Status

Accepted

## Context

After building quality, SLA, and monitoring modules that each save JSON data to S3, there was no unified view of daily pipeline health. Engineers and stakeholders needed a readable summary combining all three data sources — without requiring a running web service to serve it.

## Decision

Generate daily HTML pipeline reports using Jinja2 templates, save them to S3 under `reports/daily/YYYY/MM/DD/pipeline_report.html`, and deliver them via SMTP email. Reports combine quality score, SLA compliance, monitoring metrics, and anomaly summaries into a single styled HTML document.

## Reasons

- **No additional infrastructure needed**: S3 is already in use; Jinja2 is a pure-Python dependency with no server required.
- **HTML emails render in any email client**: Gmail, Outlook, and Apple Mail all support HTML email, so stakeholders receive a formatted report without installing anything.
- **S3 stores report history indefinitely**: Every past report is accessible by date path (`reports/daily/YYYY/MM/DD/`), providing a permanent audit trail.
- **Jinja2 already widely used in Python ecosystem**: Minimal learning curve; template syntax is familiar from Flask and Airflow's own DAG documentation feature.

## Consequences

- **Reports only accessible via S3 URL**: There is no hosted dashboard — viewing a past report requires navigating to the S3 key directly or downloading the file.
- **No interactive dashboard**: Charts, drill-downs, and filtering are not possible with static HTML. A future phase could integrate Grafana or Metabase.
- **Manual email setup required**: Recipients must configure SMTP credentials (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`) in their `.env` file; reports are silently skipped if credentials are absent.
