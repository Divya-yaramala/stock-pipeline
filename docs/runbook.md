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

## Forecasting Procedures

### Daily Forecast Check
After pipeline runs verify forecasts saved:
```
aws s3 ls s3://your-bucket/processed/forecasts_enhanced/YYYY/MM/DD/
```
Expected: 5 files (one per ticker)

### Reviewing Forecast Accuracy
Weekly accuracy review:
```python
python -c "
from ingestion.forecast_enhancer import calculate_forecast_accuracy
# Load predictions from last week and compare to actuals
predictions = [185.0, 186.0, 184.0, 187.0, 185.5]
actuals = [186.0, 185.5, 184.5, 188.0, 185.0]
accuracy = calculate_forecast_accuracy(predictions, actuals)
print('MAE:', accuracy['MAE'])
print('RMSE:', accuracy['RMSE'])
print('Directional accuracy:', accuracy['directional_accuracy'])
"
```

### Acceptable Accuracy Thresholds
- MAE < $5.00 → Good
- RMSE < $7.00 → Good
- Directional accuracy > 55% → Better than random
- If all three met: forecasts are useful

### If Accuracy Degraded
1. Check if model drift detected:
```python
python -c "from ingestion.drift_detector import run_drift_detection; import os; print(run_drift_detection('AAPL', os.getenv('AWS_BUCKET_NAME')))"
```
2. If drift detected: trigger retraining
3. Check if blend weights need adjustment:
   - If Prophet better recently: increase prophet_weight to 0.7
   - If Ensemble better recently: decrease to 0.5
4. Check volatility regime — high vol needs wider intervals

## Market Analytics Procedures

### Daily Market Graph Check
After pipeline runs verify graph analysis saved:
```
aws s3 ls s3://your-bucket/processed/graph_analysis/YYYY/MM/DD/
```

### Interpreting High Systemic Risk (density > 0.7)
When risk_level = "high":
1. All tickers highly correlated — limited diversification benefit
2. Consider reducing position sizes
3. Check if market-wide event caused correlation spike
4. Monitor for potential sharp selloff (correlated markets fall together)

```python
python -c "
from ingestion.market_graph_analyzer import calculate_market_stability
graph = {'nodes': ['AAPL','MSFT','GOOGL','AMZN','TSLA'],
         'edges': [{'source': 'AAPL', 'target': 'MSFT', 'weight': 0.9},
                   {'source': 'AAPL', 'target': 'GOOGL', 'weight': 0.85}],
         'edge_count': 2}
print(calculate_market_stability(graph))
"
```

### Weekly Sector Rotation Review
Every Monday check sector rotation:
```python
python -c "
from ingestion.sector_analyzer import calculate_sector_rotation
current = {'Technology': 0.05, 'Communication Services': 0.02, 'Consumer Discretionary': 0.08}
previous = {'Technology': 0.03, 'Communication Services': 0.04, 'Consumer Discretionary': 0.06}
print(calculate_sector_rotation(current, previous))
"
```

If Consumer Discretionary gaining and Technology losing:
- Rotation from growth to cyclicals
- Possible economic recovery signal
- Consider rebalancing portfolio

## Risk Analytics Procedures

### Daily Risk Check
After pipeline runs verify risk analysis saved:
```
aws s3 ls s3://your-bucket/processed/risk_analysis/YYYY/MM/DD/
```

### If Any Ticker Shows VERY_HIGH Risk
```python
python -c "
from ingestion.risk_analyzer import classify_risk_level, calculate_risk_metrics
import numpy as np
returns = list(np.random.normal(0.001, 0.04, 60))
metrics = calculate_risk_metrics(returns, 'TSLA')
level = classify_risk_level(metrics)
print('Risk level:', level)
print('Annual vol:', metrics.get('annualized_volatility'))
print('VaR 95%:', metrics.get('var_95'))
"
```

If VERY_HIGH:
1. Check if recent news causing volatility spike
2. Consider reducing position size
3. Check if portfolio VaR exceeds acceptable threshold
4. Alert portfolio manager

### Weekly Portfolio Optimization Review
Every Monday run optimization:
```python
python -c "
from ingestion.portfolio_optimizer import run_portfolio_optimization
import os, numpy as np
ticker_returns = {
    'AAPL': list(np.random.normal(0.001, 0.02, 60)),
    'MSFT': list(np.random.normal(0.0008, 0.018, 60)),
    'GOOGL': list(np.random.normal(0.0012, 0.022, 60)),
    'AMZN': list(np.random.normal(0.0009, 0.025, 60)),
    'TSLA': list(np.random.normal(0.0015, 0.04, 60)),
}
current_weights = {'AAPL': 0.2, 'MSFT': 0.2, 'GOOGL': 0.2, 'AMZN': 0.2, 'TSLA': 0.2}
result = run_portfolio_optimization(ticker_returns, current_weights, 10000, os.getenv('AWS_BUCKET_NAME'))
print('Max Sharpe weights:', result.get('max_sharpe', {}).get('weights'))
print('Rebalancing needed:', result.get('rebalancing_trades'))
"
```

If trades suggested:
1. Review trades for reasonableness
2. Check transaction costs (avoid tiny trades < $100)
3. Consider tax implications before executing
4. Execute trades if portfolio drifted > 5% from target

## Event-Driven Workflow Procedures

### Viewing Today's Workflow History
```python
python -c "
from ingestion.event_workflow import get_workflow_history
import os, datetime
history = get_workflow_history(
    os.getenv('AWS_BUCKET_NAME'),
    datetime.datetime.now().strftime('%Y/%m/%d')
)
print(f'Total events processed: {len(history)}')
for event in history:
    print(f'  {event.get(\"event_type\")}: {event.get(\"triggers_fired\")} triggers fired')
"
```

### Expected Daily Workflow Events
| Event | Expected Count | Notes |
|---|---|---|
| pipeline_completed | 5 | One per ticker |
| anomaly_detected | 0-5 | Only on anomaly days |
| quality_gate_blocked | 0 | Should be 0 normally |
| model_drift_detected | 0 | Only on drift days |
| sla_missed | 0 | Should be 0 normally |

### If quality_gate_blocked Events Found
This is a CRITICAL event — immediate action needed:
1. Check which ticker was blocked:
```bash
aws s3 ls s3://your-bucket/quality_gates/YYYY/MM/DD/
```
2. Check gate results:
```bash
aws s3 cp s3://your-bucket/quality_gates/YYYY/MM/DD/AAPL.json -
```
3. Follow Quality Gate Procedures (see above)

### Testing Notification Channels
```python
python -c "
from ingestion.notification_manager import run_notification_check
import os
result = run_notification_check(os.getenv('AWS_BUCKET_NAME'))
print('Channels tested:', result['channels_tested'])
print('Working:', result['working'])
print('Failed:', result['failed'])
"
```
All 3 channels should show working=3, failed=0

## Self-Service Analytics Procedures

### Building a Custom Report
```python
python -c "
from ingestion.self_service_analytics import build_custom_report
import os, datetime
result = build_custom_report(
    metrics=['M001', 'M002', 'M006'],
    tickers=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
    date=datetime.datetime.now().strftime('%Y/%m/%d'),
    bucket=os.getenv('AWS_BUCKET_NAME')
)
for ticker, metrics in result.items():
    if ticker != 'date':
        print(f'{ticker}: {metrics}')
"
```

### Data Mesh Access Request Workflow
When analytics team needs access to stock_prices (DP001):

Step 1 - Analytics team requests access:
```python
python -c "
from ingestion.data_mesh_api import request_data_access
import os
request_id = request_data_access(
    'DP001', 'analytics_team',
    'Q3 performance report', os.getenv('AWS_BUCKET_NAME')
)
print('Request ID:', request_id)
"
```

Step 2 - Data owner approves:
```python
python -c "
from ingestion.data_mesh_api import approve_access_request
import os
result = approve_access_request('REQUEST_ID_HERE', 'data_engineering', os.getenv('AWS_BUCKET_NAME'))
print('Approved:', result)
"
```

Step 3 - Analytics team gets sample:
```python
python -c "
from ingestion.data_mesh_api import get_data_product_sample
import os
sample = get_data_product_sample('DP001', 5, os.getenv('AWS_BUCKET_NAME'))
print('Sample records:', len(sample))
"
```

## Compliance Procedures

### Daily Compliance Check
Run after 11 AM EST:
```python
python -c "
from ingestion.compliance_reporter import run_compliance_reporting
import os
result = run_compliance_reporting(os.getenv('AWS_BUCKET_NAME'))
print('Overall compliant:', result.get('overall_compliant'))
print('Score:', result.get('total_score_pct'), '%')
for fw, data in result.get('frameworks', {}).items():
    status = '✅' if data.get('compliant') else '❌'
    print(f'  {status} {fw}: {data.get(\"score_pct\", 0):.1f}%')
"
```

### If Framework Non-Compliant
1. Identify failed requirements from report
2. Check specific requirement:
   - audit_trail: Are all access events being logged?
   - data_integrity: Check for unauthorized S3 modifications
   - quality_gates: Review quality_gate.py results
   - sla_compliance: Check sla_reporter.py results
3. Fix underlying issue
4. Re-run compliance check

### Weekly Suspicious Activity Review
Every Monday:
```python
python -c "
from ingestion.audit_manager import run_audit_management
import os
result = run_audit_management(os.getenv('AWS_BUCKET_NAME'))
suspicious = result.get('suspicious', [])
if suspicious:
    print('⚠️ SUSPICIOUS ACTIVITY DETECTED:')
    for s in suspicious:
        print(f'  Actor: {s.get(\"actor\")}, Category: {s.get(\"category\")}')
else:
    print('✅ No suspicious activity detected')
"
```

### Generating Compliance Certificate
```python
python -c "
from ingestion.compliance_reporter import generate_compliance_certificate
import os, datetime
cert = generate_compliance_certificate(
    'CF004',
    os.getenv('AWS_BUCKET_NAME'),
    datetime.datetime.now().strftime('%Y/%m/%d')
)
if cert.get('certified'):
    print('✅ CERTIFIED:', cert['certificate_id'])
else:
    print('❌ NOT CERTIFIED - check compliance report')
"
```

## Predictive Monitoring Procedures

### Daily Predictive Check
After pipeline runs (afternoon):
```python
python -c "
from ingestion.predictive_alerter import run_predictive_monitoring
import os
result = run_predictive_monitoring(os.getenv('AWS_BUCKET_NAME'))
if result['tickers_at_risk']:
    print('⚠️ TICKERS AT RISK:', result['tickers_at_risk'])
    print('Alert types:', result['by_type'])
else:
    print('✅ No tickers at risk')
"
```

### If Quality Degradation Predicted
1. Check current quality scores:
```python
python -c "
from ingestion.predictive_alerter import predict_quality_degradation
scores = [95, 93, 91, 89, 87, 85, 83]
result = predict_quality_degradation(scores, threshold=80.0)
print('Days until breach:', result['days_until_breach'])
print('Trend slope:', result['trend_slope'])
"
```
2. If < 3 days: run manual quality check immediately
3. Identify which quality dimension is declining
4. Fix underlying data issue before threshold breach

### Health Fingerprint Comparison
```python
python -c "
from ingestion.intelligent_monitor import (
    calculate_health_fingerprint,
    compare_health_fingerprints
)
yesterday_metrics = {'quality': 92.0, 'anomaly_rate': 5.0, 'sla': 100.0}
today_metrics = {'quality': 88.0, 'anomaly_rate': 12.0, 'sla': 83.0}
fp1 = calculate_health_fingerprint(yesterday_metrics)
fp2 = calculate_health_fingerprint(today_metrics)
changed = compare_health_fingerprints(fp1, fp2)
print('Health state changed:', changed)
"
```
If changed = True:
1. Compare yesterday vs today metrics manually
2. Identify which metrics changed
3. Investigate root cause

## Knowledge Graph Procedures

### Rebuilding Knowledge Graph
Run after adding new tickers or updating correlations:
```python
python -c "
from ingestion.knowledge_graph import build_stock_knowledge_graph
import os
result = build_stock_knowledge_graph(os.getenv('AWS_BUCKET_NAME'))
print('Entities:', result['entities_created'])
print('Relationships:', result['relationships_created'])
"
```

### Finding Related Stocks
```python
python -c "
from ingestion.knowledge_graph import find_connected_entities
import os
# Find all tech stocks
tech_stocks = find_connected_entities('Technology', 'BELONGS_TO', os.getenv('AWS_BUCKET_NAME'))
print('Tech sector stocks:', tech_stocks)

# Find AAPL competitors
competitors = find_connected_entities('AAPL', 'COMPETES_WITH', os.getenv('AWS_BUCKET_NAME'))
print('AAPL competitors:', competitors)
"
```

### Rebuilding Search Index
Run after adding new modules or ADRs:
```python
python -c "
from ingestion.semantic_search import index_pipeline_docs
import os
result = index_pipeline_docs(os.getenv('AWS_BUCKET_NAME'))
print('Indexed:', result['indexed_documents'], 'documents')
print('Terms:', result['unique_terms'], 'unique terms')
"
```

### Searching for Relevant Modules
```python
python -c "
from ingestion.semantic_search import search_pipeline_knowledge
import os
query = 'machine learning model training'
results = search_pipeline_knowledge(query, os.getenv('AWS_BUCKET_NAME'))
print(f'Results for \"{query}\":')
for r in results[:5]:
    print(f'  {r[\"id\"]}: score={r.get(\"score\", 0):.3f}')
"
```

## Report Generation Procedures

### Daily Report Generation
Run after pipeline completes (after 11 AM EST):
```python
python -c "
from ingestion.pipeline_report_generator import run_report_generation
import os
result = run_report_generation(os.getenv('AWS_BUCKET_NAME'))
exec_status = result.get('executive', {}).get('pipeline_status', 'unknown')
print('Pipeline status:', exec_status)
print('Data quality grade:', result.get('executive', {}).get('data_quality_grade'))
"
```

### Weekly Digest (Every Monday)
```python
python -c "
from ingestion.pipeline_report_generator import generate_weekly_digest
import os, datetime
week = datetime.datetime.now().strftime('%Y-W%V')
digest = generate_weekly_digest(os.getenv('AWS_BUCKET_NAME'), week)
print('Week:', week)
print('Avg quality:', digest.get('avg_quality_score'))
print('Total anomalies:', digest.get('total_anomalies'))
"
```

### Getting Recommendations
```python
python -c "
from ingestion.stock_recommender import run_recommendation_engine
import os
for profile in ['conservative', 'moderate', 'aggressive']:
    result = run_recommendation_engine(profile, os.getenv('AWS_BUCKET_NAME'))
    recs = result.get('recommendations', [])
    top = recs[0]['ticker'] if recs else 'none'
    print(f'{profile}: top pick = {top}')
"
```

## Data Validation Procedures

### Daily Validation Check
After pipeline runs verify validation reports:
```bash
aws s3 ls s3://your-bucket/validation/YYYY/MM/DD/
```
Expected: 5 files (one per ticker)

### If Pass Rate Below 80%
```python
python -c "
from ingestion.pipeline_validator import run_validation_suite, save_validation_report
import os, datetime
records = []  # Load from S3
result = run_validation_suite(records, 'AAPL')
print('Pass rate:', result['pass_rate_pct'])
for r in result['results']:
    if not r.get('passed'):
        print('FAILED:', r['rule_id'], r.get('violations', []))
"
```

1. Identify which rules are failing
2. Check raw data for the specific violations
3. Common issues:
   - V005 fails: Yahoo Finance returned bad OHLCV data
   - V004 fails: Weekend/holiday data included
   - V001 fails: API response missing fields

### Contract Health Check
```python
python -c "
from ingestion.contract_enforcer import calculate_contract_health
import os
health = calculate_contract_health('C001', os.getenv('AWS_BUCKET_NAME'))
score = health['health_score']
status = '✅ Healthy' if score >= 90 else '⚠️ Degraded' if score >= 70 else '❌ Critical'
print(f'Contract C001 health: {score:.1f}% {status}')
"
```

If health < 70%:
1. Check violation history: get_contract_violation_history('C001', bucket)
2. Identify which fields causing violations
3. Check if Yahoo Finance API changed response format
4. Update contract schema if legitimate schema change
