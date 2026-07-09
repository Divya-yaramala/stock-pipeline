# Quality Gates Guide — Stock Pipeline

## Overview
Quality gates prevent bad data from propagating downstream.
The pipeline runs 5 gates before each major stage.

## Quality Gates

| Gate | Metric | Threshold | Action |
|---|---|---|---|
| G001 freshness_gate | hours_since_update | < 25 hours | BLOCK |
| G002 completeness_gate | completeness_pct | > 80% | BLOCK |
| G003 quality_score_gate | quality_score | > 75% | WARN |
| G004 anomaly_rate_gate | anomaly_rate_pct | < 30% | WARN |
| G005 prediction_accuracy_gate | prediction_accuracy_pct | > 60% | BLOCK |

## Gate Actions
- **BLOCK**: Pipeline stops for this ticker. Auto remediation triggered.
- **WARN**: Pipeline continues but Slack warning sent.

## Auto Remediation Actions
| Issue | Action Triggered |
|---|---|
| stale_data | trigger_backfill |
| missing_files | rerun_ingestion |
| low_quality | rerun_validation |
| high_anomaly_rate | rerun_anomaly_detection |
| prediction_failure | use_fallback_model |

## Running Quality Gates
```python
# Check gates for a ticker
from ingestion.quality_gate import run_pipeline_gate_check
import os
metrics = {
    'hours_since_update': 10,
    'completeness_pct': 95.0,
    'quality_score': 88.0,
    'anomaly_rate_pct': 5.0,
    'prediction_accuracy_pct': 75.0
}
result = run_pipeline_gate_check('AAPL', metrics, os.getenv('AWS_BUCKET_NAME'))
print('Pipeline can proceed:', result)
```

## Tuning Thresholds
If gates are too aggressive (blocking valid data):
- Increase completeness threshold (e.g. 70% instead of 80%)
- Increase freshness threshold (e.g. 48h instead of 25h)
- Change `block` to `warn` for less critical gates

If gates are too lenient (bad data passing through):
- Decrease thresholds
- Add more gates for specific metrics
