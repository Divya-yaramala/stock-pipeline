# Monitoring Guide — Stock Pipeline

## Overview
The pipeline has three monitoring layers:

| Layer | Module | Purpose |
|---|---|---|
| Real-Time | realtime_monitor.py | API, lag, error rate checks |
| SLA | sla_reporter.py | 6 SLA definitions + compliance |
| Observability | data_observatory.py | Freshness, completeness, anomalies |

## Real-Time Monitor Checks

| Check | Interval | What It Monitors |
|---|---|---|
| M001 api_availability | 5 min | Yahoo Finance API up/down |
| M002 data_freshness | 1 hour | S3 data age per ticker |
| M003 pipeline_lag | 10 min | Processing delay |
| M004 error_rate | 15 min | DLQ events / total events |
| M005 resource_usage | 5 min | CPU, memory, disk |

## SLA Definitions

| SLA | Target Time | Description |
|---|---|---|
| SLA001 daily_ingestion | 7 AM EST | Data ingested |
| SLA002 anomaly_detection | 8 AM EST | Anomalies detected |
| SLA003 predictions_ready | 9 AM EST | Forecasts ready |
| SLA004 insights_generated | 10 AM EST | GPT insights done |
| SLA005 snowflake_sync | 11 AM EST | Warehouse synced |
| SLA006 dashboard_updated | 11 AM EST | Dashboard current |

## Running Monitors
```bash
# Single monitor cycle
python -c "from ingestion.realtime_monitor import run_monitor_cycle; import os; print(run_monitor_cycle(os.getenv('AWS_BUCKET_NAME')))"

# SLA report
python -c "from ingestion.sla_reporter import run_sla_reporting; import os; print(run_sla_reporting(os.getenv('AWS_BUCKET_NAME')))"
```

## Interpreting Results
- `api_availability: False` → Yahoo Finance outage → wait and retry
- `pipeline_lag > 60 min` → pipeline stalled → check Airflow
- `error_rate > 5%` → DLQ filling up → check dead_letter_queue.py
- `SLA compliance < 90%` → escalate to on-call engineer

## Layer 5: Distributed Tracing (distributed_tracer.py)
Captures full pipeline execution timeline:
- trace_id per pipeline run
- span per pipeline step
- slowest_span detection
- error_span identification

## Layer 6: Observability Dashboard (observability_dashboard.py)
Google SRE golden signals:
- latency: avg pipeline duration
- traffic: records per hour
- errors: DLQ rate
- saturation: resource utilization

SLO compliance tracking:
- 5 objectives checked daily
- violations logged and alerted

## Complete 6-Layer Monitoring Stack
| Layer | Tool | Frequency |
|---|---|---|
| 1. Real-time | realtime_monitor.py | Every 5-15 min |
| 2. SLA | sla_reporter.py | Daily |
| 3. Observability | observability_dashboard.py | Daily |
| 4. Predictive | predictive_alerter.py | Daily |
| 5. Intelligent | intelligent_monitor.py | Daily |
| 6. Tracing | distributed_tracer.py | Per pipeline run |

---

## Monitoring Stack Complete! 🎉
All 6 monitoring layers implemented:

| Layer | Module | Day Built |
|---|---|---|
| Real-Time | realtime_monitor.py | Day 62 |
| SLA | sla_reporter.py | Day 62 |
| Observability | observability_dashboard.py | Day 88 |
| Predictive | predictive_alerter.py | Day 80 |
| Intelligent | intelligent_monitor.py | Day 80 |
| Tracing | distributed_tracer.py | Day 88 |
