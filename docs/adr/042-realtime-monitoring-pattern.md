# ADR 042 - Real-Time Monitoring Pattern

## Status
Accepted

## Context
Daily pipeline runs complete by ~11 AM EST, but issues can arise at any point: Yahoo Finance
API outages, S3 write failures, resource exhaustion, or DLQ spikes. Waiting until the next
Airflow run to discover a problem means hours of silent data staleness. We needed continuous
visibility between daily runs without building a separate monitoring infrastructure.

## Decision
Built a real-time monitor in `ingestion/realtime_monitor.py` with 5 check types that run on
configurable intervals and persist results to S3:

| Check | Interval | What It Catches |
|---|---|---|
| M001 api_availability | 5 min | Yahoo Finance outages |
| M002 data_freshness | 60 min | Stale data not refreshed |
| M003 pipeline_lag | 10 min | Stalled processing |
| M004 error_rate | 15 min | DLQ spikes |
| M005 resource_usage | 5 min | CPU/memory/disk pressure |

Results are written to `monitoring/realtime/YYYY/MM/DD/` in S3 for historical trending.

## Reasons
- **Early detection**: API outages detected within 5 minutes instead of next daily run
- **Configurable intervals**: each check runs at its own cadence appropriate to the signal
- **S3 persistence**: all check results form a time-series for trend analysis
- **No new infrastructure**: runs as a Python process; deployable as Lambda or cron job
- **Composable**: `run_monitor_cycle()` orchestrates all checks in one call

## Consequences
- Monitor process must remain running continuously (not currently wired to Airflow)
- yfinance API calls during monitoring count against rate limits
- Future: deploy as AWS Lambda triggered by CloudWatch Events every 5 minutes
