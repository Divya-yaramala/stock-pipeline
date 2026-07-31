# ADR 082 - Report Generation Strategy

## Status
Accepted

## Context
Different stakeholders need different report formats. Business stakeholders need a high-level status summary they can act on without understanding the pipeline internals. Engineers need detailed technical metrics. All teams benefit from a weekly trend view.

## Decision
Built 3 report types — executive summary, technical report, and weekly digest — each targeting a different audience and saved to S3 for historical access.

## Reasons
- Executive summary for business stakeholders: non-technical language, pipeline status, data quality grade, key insights
- Technical report for engineers: test results, performance benchmarks, error rates, bottleneck analysis
- Weekly digest for trend analysis: 7-day quality trend, SLA compliance trend, top and worst-performing tickers
- HTML format renders in email and browser without additional tooling
- All reports saved to S3 for historical access and audit trail

## Consequences
- Reports require pre-computed metrics to be meaningful — meaningless if pipeline hasn't run yet
- Manual distribution still needed — no auto-email yet
- HTML generation is a simple template render, not a full templating engine
- Future: auto-email executive summary daily at 11 AM EST using SES or SMTP
