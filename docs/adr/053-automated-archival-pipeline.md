# ADR 053 — Automated Archival Pipeline

## Status
Accepted

## Context
Manual archival is error-prone and easy to forget. Without automation, data accumulates indefinitely in S3 Standard storage, paying $0.023/GB for data that hasn't been accessed in months. A manual process relying on an engineer remembering to archive data weekly will eventually fail.

## Decision
Built an automated archival pipeline (`data_archiver.py`) with the following design:
- 6 policies covering all major S3 prefixes with separate archive and delete thresholds
- Dry-run mode mandatory before actual execution (default `dry_run=True`)
- Separate thresholds: archive to Glacier after N days, delete permanently after M days (M > N)
- Archival report saved to `reports/archival/YYYY/MM/DD/report.json` for audit trail
- Weekly schedule recommended (Sunday 2 AM via cron or Airflow)

## Reasons
1. **6 policies cover all major prefixes**: raw/stocks, anomalies, predictions, insights, sentiment, model experiments — each with appropriate retention based on access patterns
2. **Dry-run first**: Forces review before irreversible operations; operator must explicitly pass `dry_run=False`
3. **Archive then delete**: Two-stage lifecycle (HOT → COLD → deleted) gives a recovery window between archival and deletion
4. **S3 audit trail**: Report saved to S3 ensures archival history is durable and reviewable

## Consequences
- Must review dry-run report before executing — no fully automated deletion without human review
- Glacier retrieval delay (3-5 minutes expedited, 3-5 hours standard) if archived data is needed urgently
- S3 Standard-IA 30-day minimum charge applies to WARM tier — avoid moving objects that will be re-accessed within 30 days
- Future: use AWS EventBridge to schedule weekly archival automatically and notify via Slack
