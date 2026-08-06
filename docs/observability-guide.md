# Observability Guide — Stock Pipeline

## Overview
The pipeline implements full-stack observability using
distributed tracing and Google SRE principles.

## Google SRE Golden Signals

### 1. Latency
Metric: Average pipeline duration in minutes
Target: < 45 minutes for full daily pipeline
Alert: > 60 minutes → investigate bottleneck

### 2. Traffic
Metric: Records processed per hour
Target: 5 tickers × ~252 days = 1260 records/year
Alert: < 5 records/day → ingestion issue

### 3. Errors
Metric: Error rate percentage (DLQ events / total)
Target: < 5%
Alert: > 10% → data quality investigation

### 4. Saturation
Metric: Resource utilization (CPU + memory + disk)
Target: < 80% on any dimension
Alert: > 90% → add capacity

## Service Level Objectives (SLOs)

| SLO | Target | Measurement |
|---|---|---|
| pipeline_availability | 99.5% uptime | Successful runs / total runs |
| data_freshness | < 25 hours | Hours since last update |
| quality_score | > 90% | Average quality score |
| prediction_accuracy | > 70% | RMSE-based accuracy |
| api_latency | < 500ms p95 | API response time |

## Distributed Tracing

### Trace Structure
```
trace_id → spans:
  span_1: fetch_data (3.2s)
  span_2: validate (0.8s)
  span_3: detect_anomaly (4.1s) ← slowest
  span_4: predict (12.3s)
  span_5: generate_insights (6.7s)
Total: 27.1s
```

### Finding Slow Spans
```python
python -c "
from ingestion.distributed_tracer import get_trace, analyze_trace
import os
trace = get_trace('YOUR_TRACE_ID', os.getenv('AWS_BUCKET_NAME'))
analysis = analyze_trace(trace)
print('Slowest:', analysis['slowest_span'])
print('Total:', analysis['total_ms'], 'ms')
"
```

### Error Span Investigation
If error_count > 0:
1. Find error spans in trace
2. Check span metadata for error message
3. Correlate with audit logs
4. Apply recovery strategy

## Running Observability Checks
```python
# Full observability report
python -c "
from ingestion.observability_dashboard import run_observability_check
import os
result = run_observability_check(os.getenv('AWS_BUCKET_NAME'))
for signal, value in result.get('golden_signals', {}).items():
    print(f'{signal}: {value}')
"
```
