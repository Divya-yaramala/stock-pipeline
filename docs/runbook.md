# Runbook — Stock Pipeline

This document covers operational procedures for the AI-powered stock price pipeline.

---

## Alert Response Procedures

### 🚨 Anomaly Alert Response
1. Check Slack for ticker and anomaly label (SPIKE/DROP/VOLUME)
2. Verify in dashboard: http://localhost:8503
3. Check raw data: aws s3 ls s3://bucket/raw/stocks/YYYY/MM/DD/TICKER/
4. If data corruption: run rollback script
   python scripts/rollback_pipeline.py --ticker AAPL --step prices --version-id abc12345
5. If genuine anomaly: no action needed — pipeline handles automatically

### ⚠️ Quality Warning Response
1. Check quality score in Slack message
2. Run quality scorer:
   python -c "from ingestion.quality_scorer import run_quality_scoring; import os, datetime; print(run_quality_scoring(os.getenv('AWS_BUCKET_NAME'), datetime.datetime.now().strftime('%Y/%m/%d')))"
3. Identify which dimension is failing (completeness, accuracy, etc.)
4. Check S3 for missing files if completeness issue
5. Re-run affected pipeline step if needed

### ❌ Pipeline Failure Response
1. Check Airflow UI: http://localhost:8080
2. Find failed task and check logs
3. Common fixes:
   - API timeout: re-run task manually in Airflow
   - S3 permission: check AWS credentials in .env
   - DB connection: check POSTGRES_HOST in .env
4. After fix: clear failed task and re-run in Airflow

---

## Weekly Maintenance Schedule

### Every Monday
- Check GitHub Actions — all green?
- Review Slack alerts from past week
- Check S3 storage quota

### Every Sunday (automated via cron)
- Run S3 optimizer (dry_run=True first!)
- Run health scorer
- Generate weekly quality trend report

### Monthly
- Review ADRs — any decisions to update?
- Update project-stats.md with current counts
- Review AWS costs in Cost Explorer
- Rotate secrets (90-day policy)

### Commands for Weekly Maintenance

```bash
# Check all systems
python scripts/health_check.py

# Run S3 optimization (dry run)
python -c "from ingestion.s3_optimizer import run_s3_optimization; import os; print(run_s3_optimization(os.getenv('AWS_BUCKET_NAME'), dry_run=True))"

# Check resource usage
python -c "from ingestion.resource_manager import run_resource_check; import os; print(run_resource_check(os.getenv('AWS_BUCKET_NAME')))"
```

---

## Configuration Validation

### Before Every Pipeline Run
```bash
python scripts/validate_secrets.py
```

### Expected Output (all green)
```
=== REQUIRED SECRETS ===
  AWS            ✅ ok
  PostgreSQL     ✅ ok
  Snowflake      ✅ ok

=== OPTIONAL SECRETS ===
  OpenAI         ✅ ok
  Slack          ✅ ok
  Email          ⚠️  missing: SMTP_HOST, SMTP_USER (not required)
```

### If Required Secret Missing
```
ERROR: Required secrets are missing — pipeline cannot run
```
Fix: Add the missing variable to `.env` and re-run `validate_secrets.py`.

### Config Summary (safe to share — never shows secrets)
```bash
python -c "from ingestion.config_manager import get_config_summary; print(get_config_summary())"
# Output: {"tickers": ["AAPL", ...], "region": "us-east-1", "chaos_enabled": false}
```

---

## Quality Gate Procedures

### When a Gate Blocks the Pipeline
1. Check which gate failed in Slack alert
2. Run gate check manually:
```python
from ingestion.quality_gate import run_quality_gates
metrics = {'hours_since_update': 30, 'completeness_pct': 95.0,
           'quality_score': 88.0, 'anomaly_rate_pct': 5.0,
           'prediction_accuracy_pct': 75.0}
print(run_quality_gates(metrics, 'AAPL'))
```
3. Check auto remediation history:
```python
from ingestion.auto_remediation import get_remediation_history
import os
print(get_remediation_history('AAPL', os.getenv('AWS_BUCKET_NAME')))
```
4. Fix underlying issue (see Alert Response Procedures above)
5. Re-run blocked pipeline step in Airflow

### Common Gate Failures
- **G001 freshness_gate**: Yahoo Finance API rate limit hit → wait 1 hour
- **G002 completeness_gate**: S3 upload failed → check AWS credentials
- **G005 prediction_accuracy_gate**: Model drift → trigger retraining

---

## SLA Monitoring Procedures

### Daily SLA Check
Run after each pipeline execution to confirm all stages completed on time:
```python
from ingestion.sla_reporter import run_sla_reporting
import os
report = run_sla_reporting(os.getenv('AWS_BUCKET_NAME'))
print(report)
```

### SLA Status Thresholds
| Compliance | Status | Action |
|---|---|---|
| ≥ 90% | 🟢 Green | No action needed |
| 70–89% | 🟡 Yellow | Investigate slow stages |
| < 70% | 🔴 Red | Escalate to on-call engineer |

### When an SLA Is Missed
1. Identify which SLA failed in the daily report (`met: false`)
2. Check Airflow logs for the corresponding task
3. Run the stage manually if safe to do so
4. Record the miss and root cause in the incident log
5. If missed 3+ days in a row, review pipeline capacity

### Weekly SLA Review
1. Pull 30-day compliance trend:
```python
from ingestion.sla_reporter import get_sla_trend
import os
trend = get_sla_trend(os.getenv('AWS_BUCKET_NAME'), days=30)
print(trend['avg_compliance_pct'], trend['trend'])
```
2. If `trend == "declining"` → investigate systemic bottlenecks
3. Share compliance % with stakeholders each Monday

---

## Experiment Management Procedures

### Creating a New Experiment
```python
from ingestion.experiment_manager import create_experiment
import os
exp_id = create_experiment(
    name='prophet_vs_ensemble',
    description='Compare Prophet vs Ensemble model accuracy',
    variants=['prophet', 'ensemble'],
    bucket=os.getenv('AWS_BUCKET_NAME')
)
print('Experiment ID:', exp_id)
```

### Checking Which Variant a Ticker Gets
```python
from ingestion.experiment_manager import get_variant
import os
variant = get_variant('EXP_ID_HERE', 'AAPL', os.getenv('AWS_BUCKET_NAME'))
print('AAPL gets variant:', variant)
```

### Analyzing Experiment Results
```python
from ingestion.experiment_manager import analyze_experiment
import os
results = analyze_experiment('EXP_ID_HERE', os.getenv('AWS_BUCKET_NAME'))
print('Winner:', results['winner'])
```

### Concluding an Experiment
```python
from ingestion.experiment_manager import conclude_experiment
import os
conclusion = conclude_experiment('EXP_ID_HERE', os.getenv('AWS_BUCKET_NAME'))
print('Conclusion:', conclusion)
```

---

## Event Bus Procedures

### Viewing Today's Events
```python
from ingestion.event_bus import get_event_summary
import os, datetime
summary = get_event_summary(
    os.getenv('AWS_BUCKET_NAME'),
    datetime.datetime.now().strftime('%Y/%m/%d')
)
print('Total events:', summary['total'])
print('By type:', summary['by_type'])
```

### Expected Daily Events
- data_ingested: 5 (one per ticker)
- anomaly_detected: 0-5 (varies)
- prediction_generated: 5 (one per ticker)
- quality_gate_passed: 5+ (multiple gates per ticker)
- sla_met: 6 (all SLAs met on good days)
- pipeline_completed: 5 (one per ticker)

### If Events are Missing
1. Check Airflow for failed tasks: http://localhost:8080
2. Check S3 events prefix:
   aws s3 ls s3://bucket/events/YYYY/MM/DD/
3. Check pipeline logs for event publish errors
4. Re-run failed pipeline steps to regenerate events

### Publishing Manual Event
```python
from ingestion.event_bus import publish_event
import os
event_id = publish_event(
    'pipeline_completed',
    {'ticker': 'AAPL', 'duration_minutes': 45.0},
    'manual',
    os.getenv('AWS_BUCKET_NAME')
)
print('Published event:', event_id)
```

---

## Schema Registry Procedures

### Setting Up Schema Registry
Run once at pipeline initialization:
```bash
python -c "from ingestion.schema_registry import run_schema_registry_setup; import os; run_schema_registry_setup(os.getenv('AWS_BUCKET_NAME'))"
```

### Adding a New Schema Version
1. Get current schema:
```bash
python -c "from ingestion.schema_registry import get_latest_schema; import os; import json; print(json.dumps(get_latest_schema('stock_prices_raw', os.getenv('AWS_BUCKET_NAME')), indent=2))"
```

2. Check if changes are safe:
```python
from ingestion.schema_registry import validate_schema_evolution
old = {'ticker': {'type': 'string'}, 'close_price': {'type': 'float'}}
new = {'ticker': {'type': 'string'}, 'close_price': {'type': 'float'}, 'adj_close': {'type': 'float', 'required': False}}
print(validate_schema_evolution(old, new))
```

3. If safe: register new version
```python
from ingestion.schema_registry import register_schema
import os
schema_def = {'ticker': {'type': 'string'}, 'close_price': {'type': 'float'}, 'adj_close': {'type': 'float'}}
print(register_schema('stock_prices_raw', schema_def, '1.1.0', os.getenv('AWS_BUCKET_NAME')))
```

### If Breaking Change Detected
- Do NOT proceed with schema change
- Coordinate with all consumer teams first
- Create new schema name instead: stock_prices_raw_v2
- Maintain old schema until consumers migrate

---

## Weekly Archival Schedule

### Every Sunday at 2 AM (recommended)

Step 1: Run dry run
```bash
python -c "from ingestion.data_archiver import run_archival_pipeline; import os; print(run_archival_pipeline(os.getenv('AWS_BUCKET_NAME'), dry_run=True))"
```

Step 2: Review report
```bash
aws s3 cp s3://your-bucket/reports/archival/YYYY/MM/DD/report.json ./archival_report.json
cat archival_report.json
```

Step 3: If report looks correct, execute
```bash
python -c "from ingestion.data_archiver import run_archival_pipeline; import os; print(run_archival_pipeline(os.getenv('AWS_BUCKET_NAME'), dry_run=False))"
```

Step 4: Check tier costs after archival
```python
from ingestion.storage_tier_manager import calculate_tier_costs
import os
print(calculate_tier_costs(os.getenv('AWS_BUCKET_NAME')))
```

### Monthly Storage Review
Check total S3 costs in AWS Cost Explorer:
- Navigate to AWS Console → Cost Explorer
- Filter by S3 service
- Compare month-over-month storage costs
- If costs rising: check archival ran last Sunday

### If Archived Data Needed Urgently
1. Identify the S3 key needed
2. Request Glacier retrieval (3-5 min expedited):
```bash
aws s3api restore-object \
  --bucket your-bucket \
  --key your/archived/file.json \
  --restore-request Days=7,GlacierJobParameters={Tier=Expedited}
```
3. Wait 3-5 minutes then download
4. Remember to re-archive after use!

---

## Data Privacy Incident Procedures

### If PII Found in Pipeline Data
1. Immediately run PII scan to confirm:
```bash
python -c "from ingestion.pii_detector import run_pii_scan; import os; print(run_pii_scan(os.getenv('AWS_BUCKET_NAME'), 'raw/stocks/'))"
```

2. Identify affected files from scan report
3. Mask PII in affected files:
```python
from ingestion.pii_detector import mask_pii
import os, boto3, json
s3 = boto3.client('s3')
obj = s3.get_object(Bucket=os.getenv('AWS_BUCKET_NAME'), Key='affected/file.json')
data = json.loads(obj['Body'].read())
masked = mask_pii(data)
s3.put_object(Bucket=os.getenv('AWS_BUCKET_NAME'), Key='affected/file.json', Body=json.dumps(masked))
```
4. Document incident in audit log
5. Check if downstream consumers received unmasked data
6. Escalate to security team if SSN or CC data found

### Privacy Policy Violation Response
1. Run policy compliance check:
```bash
python -c "from ingestion.data_privacy_manager import generate_privacy_report; import os; print(generate_privacy_report(os.getenv('AWS_BUCKET_NAME')))"
```
2. Identify violating datasets
3. Fix classification or retention settings
4. Re-run compliance check to confirm fix

---

## Performance Testing Procedures

### Weekly Benchmark Run
Run every Monday to detect regressions:
```bash
python -c "from ingestion.performance_benchmarker import run_benchmark_suite; import os; print(run_benchmark_suite(os.getenv('AWS_BUCKET_NAME')))"
```

### Interpreting Benchmark Results
Expected baseline performance:
- S3 put: < 200ms average
- S3 get: < 150ms average
- S3 list: < 100ms average
- Data validation: > 1000 records/second
- Feature engineering: > 500 records/second

### If Regression Detected (>20% slower)
1. Check AWS CloudWatch for S3 latency spikes
2. Check system resources:
```bash
python -c "from ingestion.resource_manager import run_resource_check; import os; print(run_resource_check(os.getenv('AWS_BUCKET_NAME')))"
```
3. Check if new code introduced O(n²) operation
4. Profile the slow function:
```python
import cProfile
from ingestion.your_slow_module import slow_function
cProfile.run('slow_function()')
```
5. Fix regression before merging to main

### Coverage Check Procedure
Run weekly to ensure coverage not declining:
```bash
pytest tests/ --cov=ingestion --cov-report=term-missing 2>&1 | tail -20
```

If total coverage < 80%:
1. Find uncovered files: look for lines with "Miss" in report
2. Add tests for uncovered functions
3. Re-run coverage to verify improvement

## Streaming Analytics Monitoring

### Daily Stream Processing Check
After pipeline runs verify streaming results saved:
```bash
aws s3 ls s3://your-bucket/streaming/analytics/YYYY/MM/DD/
```
Expected: 5 files (one per ticker)

### If Streaming Results Missing
1. Check if Kafka streaming is enabled:
```bash
python -c "from ingestion.feature_flag_manager import is_enabled; import os; print(is_enabled('enable_kafka_streaming', os.getenv('AWS_BUCKET_NAME')))"
```

2. If disabled, run batch streaming analytics:
```bash
python -c "
from ingestion.streaming_analytics import process_price_stream, save_stream_results
import os, datetime
prices = [185.0 + i * 0.1 for i in range(30)]
results = process_price_stream('AAPL', prices, window_size=20)
save_stream_results('AAPL', results, os.getenv('AWS_BUCKET_NAME'), datetime.datetime.now().strftime('%Y/%m/%d'))
print('Saved streaming results for AAPL')
"
```

### VWAP Monitoring
If VWAP significantly different from close price:
- Price much above VWAP → overbought intraday
- Price much below VWAP → oversold intraday
- Large divergence → investigate unusual volume

## Pipeline Optimization Procedures

### Weekly Performance Review
Run pipeline profiling every Monday:
```bash
python -c "from ingestion.pipeline_optimizer import run_pipeline_profiling; import os; print(run_pipeline_profiling(os.getenv('AWS_BUCKET_NAME')))"
```

### If Bottleneck Detected
1. Check which step is slow from profiling report
2. Get optimization recommendations:
```bash
python -c "
from ingestion.pipeline_optimizer import generate_optimization_recommendations
bottlenecks = [{'step': 'price_predict', 'duration_seconds': 18.5}]
recs = generate_optimization_recommendations(bottlenecks)
for rec in recs:
    print(rec)
"
```

3. Common optimizations:
   - Slow fetch: enable caching (feature flag: enable_cache)
   - Slow predict: reduce Prophet changepoint_prior_scale
   - Slow Snowflake: upgrade warehouse size in Snowflake UI
   - Slow S3: increase max_workers in batch uploads

### Checking Pipeline Efficiency Score
```bash
python -c "
from ingestion.pipeline_optimizer import calculate_pipeline_efficiency
profiles = [
    {'step': 'fetch', 'duration_seconds': 5.0},
    {'step': 'validate', 'duration_seconds': 0.5},
    {'step': 'anomaly', 'duration_seconds': 3.0},
]
print(calculate_pipeline_efficiency(profiles))
"
```
Healthy efficiency score: > 50%
Low efficiency score (<30%): one step dominates — needs optimization


## NLP Monitoring Procedures

### Daily NLP Check
After pipeline runs verify NLP results saved:
```
aws s3 ls s3://your-bucket/processed/nlp/YYYY/MM/DD/
```
Expected: 5 files (one per ticker AAPL MSFT GOOGL AMZN TSLA)

### If NLP Results Missing
Run NLP analysis manually:
```python
python -c "
from ingestion.nlp_processor import run_nlp_analysis
import os
texts = [
    'Apple reported strong Q3 earnings beating estimates.',
    'AAPL stock surged after bullish analyst upgrades.'
]
result = run_nlp_analysis('AAPL', texts, os.getenv('AWS_BUCKET_NAME'))
print('Sentiment:', result.get('sentiment', 'unknown'))
"
```

### Reviewing Sentiment Accuracy
Weekly spot check — compare NLP sentiment vs price movement:
```python
python -c "
from ingestion.nlp_processor import calculate_text_sentiment
headlines = [
    'Apple beats earnings with record iPhone sales',
    'AAPL stock upgraded by Goldman Sachs to Buy',
]
for h in headlines:
    result = calculate_text_sentiment(h)
    print(f'{h[:50]}... -> {result[\"label\"]}')
"
```

If sentiment frequently wrong:
- Add new financial terms to FINANCIAL_TERMS dict
- Consider upgrading to FinBERT model
