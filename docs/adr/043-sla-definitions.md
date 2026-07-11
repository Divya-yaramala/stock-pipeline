# ADR 043 - SLA Definitions for Stock Pipeline

## Status
Accepted

## Context
Without explicit SLA targets, pipeline health is subjective — "it ran" is not the same as
"it ran on time." Stakeholders and on-call engineers needed measurable, agreed-upon targets
for each pipeline stage so that compliance could be tracked objectively over time.

## Decision
Defined 6 SLAs in `ingestion/sla_reporter.py`, each with a specific target completion hour
in EST that maps to a daily pipeline stage:

| SLA | Stage | Target Hour |
|---|---|---|
| SLA001 | Data ingestion | 7 AM |
| SLA002 | Anomaly detection | 8 AM |
| SLA003 | Price predictions | 9 AM |
| SLA004 | GPT market insights | 10 AM |
| SLA005 | Snowflake sync | 11 AM |
| SLA006 | Dashboard update | 11 AM |

Compliance is measured as `(SLAs met / total SLAs) × 100`, reported daily and trended over
30 days. Results are saved to `sla/reports/YYYY/MM/DD/report.json`.

## Reasons
- **Clear targets**: hour-based SLAs are unambiguous and match the batch cadence
- **Full-pipeline coverage**: 6 SLAs span ingestion through dashboard, leaving no blind spots
- **Objective measurement**: compliance % enables stakeholder reporting without interpretation
- **Trend detection**: 30-day trend distinguishes one-off failures from systemic degradation
- **Shareable reports**: JSON reports can be forwarded to stakeholders or piped into dashboards

## Consequences
- SLA targets assume pipeline runs Monday–Friday; weekends are not handled
- EST target hours are hard-coded — would need adjustment if pipeline moves to a different TZ
- Completion records must be written by each pipeline module to trigger SLA tracking
- Future: add weekday/weekend SLA variants and alert on `trend: declining` automatically
