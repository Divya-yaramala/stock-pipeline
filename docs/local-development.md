# Local Development Guide

This guide walks through setting up the stock pipeline for local development, running the test suite, and extending the project.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Setup Steps](#setup-steps)
- [Running Tests](#running-tests)
- [Common Errors](#common-errors)
- [Adding a New Ticker](#adding-a-new-ticker)
- [Backfilling Historical Data](#backfilling-historical-data)

---

## 1. Prerequisites

Ensure the following are installed and available before starting:

| Requirement | Minimum Version | Purpose |
|-------------|----------------|---------|
| Python | 3.11 | Runtime for all pipeline scripts |
| Docker Desktop | 4.x | Runs Postgres and Airflow containers |
| AWS account | — | S3 bucket for raw and processed data |
| Snowflake account | — | Cloud data warehouse (free trial available) |
| OpenAI API key | — | GPT-3.5 market insight generation |

---

## 2. Setup Steps

### Clone and configure environment

```bash
# 1. Clone the repository
git clone https://github.com/Divya-yaramala/stock-pipeline.git
cd stock-pipeline

# 2. Copy the environment template and fill in your credentials
cp .env.example .env
# Edit .env with your AWS keys, Snowflake credentials, and OpenAI API key

# 3. Install Python dependencies
pip install -r requirements.txt
```

### Start the database

```bash
# 4. Start Postgres and Airflow via Docker Compose
docker-compose up -d

# 5. Initialise the Postgres staging schema
python scripts/setup_postgres.py

# 6. (Optional) Initialise Snowflake objects — requires valid Snowflake credentials in .env
python scripts/setup_snowflake.py
```

### Run the pipeline locally

```bash
# 7. Run the full pipeline end-to-end without Airflow
python scripts/run_pipeline_local.py
```

This script runs each step sequentially, prints timing for each stage, and produces a summary table on completion.

### Access the Airflow UI

```bash
# 8. Check that all services are healthy
python scripts/check_airflow.py

# 9. Open the Airflow web UI
# URL: http://localhost:8080
# Username: admin  Password: admin
```

---

## 3. Running Tests

```bash
# Run all 40 tests with verbose output
pytest tests/ -v

# Run a specific test file
pytest tests/test_fetch_stocks.py -v

# Run tests matching a name pattern
pytest tests/ -k "anomaly" -v

# Run with short traceback (useful for CI-style output)
pytest tests/ --tb=short

# Run linting before tests (mirrors CI)
flake8 ingestion/ scripts/ tests/ --max-line-length=100 --ignore=E402,W503
black --check ingestion/ scripts/ tests/
isort --check-only ingestion/ scripts/ tests/
```

---

## 4. Common Errors and Fixes

### Error: `ModuleNotFoundError: No module named 'ingestion'`

**Cause:** Python cannot find the `ingestion` package because the project root is not on `sys.path`.

**Fix:**
```bash
# Option A — run pytest from the project root (recommended)
cd stock-pipeline
pytest tests/ -v

# Option B — set PYTHONPATH explicitly
PYTHONPATH=. pytest tests/ -v
```

The `pytest.ini` at the project root sets `pythonpath = .` automatically, so this should not occur when running pytest normally.

---

### Error: `botocore.exceptions.NoCredentialsError`

**Cause:** AWS credentials are missing or not loaded from `.env`.

**Fix:**
```bash
# Ensure .env is populated with real credentials
cat .env | grep AWS

# Load .env before running (if not using python-dotenv automatically)
export $(cat .env | xargs) && python scripts/run_pipeline_local.py
```

All ingestion scripts use `os.environ.get()`, so the credentials must be set as environment variables before the script runs.

---

### Error: `psycopg2.OperationalError: could not connect to server`

**Cause:** The Postgres container is not running, or `POSTGRES_HOST` points to the wrong address.

**Fix:**
```bash
# Check that the Postgres container is running
docker ps | grep postgres

# If not running, start it
docker-compose up -d postgres

# For local scripts (outside Docker), set POSTGRES_HOST=localhost in .env
# For scripts running inside Docker, use POSTGRES_HOST=postgres
```

---

### Error: `prophet` installation fails with compiler errors

**Cause:** Prophet requires `pystan` which compiles C++ code. Missing build tools on Windows or macOS.

**Fix:**
```bash
# Windows — install via conda which provides pre-built binaries
conda install -c conda-forge prophet

# macOS — install Xcode command-line tools first
xcode-select --install
pip install prophet
```

---

### Error: `snowflake.connector.errors.DatabaseError: 250001`

**Cause:** The `SNOWFLAKE_ACCOUNT` value in `.env` is incorrect. Snowflake account identifiers have a specific format.

**Fix:**
```bash
# The account identifier format is: <orgname>-<accountname>
# Example: myorg-myaccount  (NOT the full URL)
# Find it in: Snowflake UI → Admin → Accounts → copy the account identifier
```

---

## 5. Adding a New Ticker

To add a sixth ticker (e.g., `NVDA`) to the pipeline:

1. **Update the tickers list** in `ingestion/fetch_stocks.py`, `ingestion/anomaly_detector.py`, `ingestion/price_predictor.py`, `ingestion/market_insights.py`, and `ingestion/snowflake_sync.py`:
   ```python
   TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]
   ```

2. **Verify the ticker is valid** — run a quick fetch to confirm yfinance returns data:
   ```python
   import yfinance as yf
   df = yf.download("NVDA", period="5d")
   print(df)
   ```

3. **Add a seed entry** if the project uses a `stock_symbols.csv` seed in dbt:
   ```
   symbol,name,sector
   NVDA,NVIDIA Corporation,Technology
   ```

4. **Run the pipeline locally** to confirm data flows end-to-end for the new ticker:
   ```bash
   python scripts/run_pipeline_local.py
   ```

5. **Update tests** — add the new ticker to any test fixtures that enumerate the full ticker list.

---

## 6. Backfilling Historical Data

Use `scripts/backfill.py` to load historical data for any date range without re-running the full Airflow DAG.

```bash
# Backfill last 30 days for all tickers
python scripts/backfill.py --start-date 2024-01-01 --end-date 2024-01-31

# Backfill a specific ticker
python scripts/backfill.py --ticker AAPL --start-date 2024-01-01

# Dry run to preview what would be loaded without making changes
python scripts/backfill.py --start-date 2024-01-01 --dry-run
```

The incremental loader also runs automatically as part of the Airflow DAG (`run_incremental_load` task). It queries Postgres for each ticker's latest `trade_date` and backfills any gaps detected since that date.

To force a full re-fetch instead of incremental loading, trigger the DAG with `full_refresh=True` in the Airflow UI under **Trigger DAG w/ config**.


---

## 7. Validating Your Environment

Before running the pipeline, verify all required secrets are set:

```bash
# Check all required secrets are set
python scripts/validate_secrets.py
```

The script checks every required env var grouped by service (AWS, Postgres, Snowflake, OpenAI) and prints a status table. It exits with code `1` if any required variable is missing. The Slack webhook is optional — a warning is shown but the script still exits `0`.

You can also validate configs programmatically at pipeline startup:

```python
from ingestion.config_manager import validate_all_configs

if not validate_all_configs():
    raise SystemExit("Missing required environment configuration")
```

## Cost Optimization

```bash
# Dry-run: preview which objects would be deleted (safe, no changes made)
python -c "
import os
from ingestion.s3_optimizer import run_s3_optimization
print(run_s3_optimization(os.getenv('AWS_BUCKET_NAME', 'my-bucket'), dry_run=True))
"

# Live run: delete expired objects according to retention policies
python -c "
import os
from ingestion.s3_optimizer import run_s3_optimization
print(run_s3_optimization(os.getenv('AWS_BUCKET_NAME', 'my-bucket'), dry_run=False))
"

# Check size and estimated cost for a specific prefix
python -c "
import os
from ingestion.s3_optimizer import calculate_prefix_size, calculate_cost_savings
info = calculate_prefix_size(os.getenv('AWS_BUCKET_NAME', 'my-bucket'), 'raw/stocks')
savings = calculate_cost_savings(info['total_size_mb'] / 1024, 'delete')
print(info, savings)
"

# Move old raw data to Glacier instead of deleting it
python -c "
import os
from ingestion.s3_optimizer import identify_expired_objects, move_to_glacier
bucket = os.getenv('AWS_BUCKET_NAME', 'my-bucket')
keys = identify_expired_objects(bucket, 'raw/stocks', retention_days=90)
print(move_to_glacier(bucket, keys))
"
```

## Resource Monitoring

```bash
# Check current CPU / memory / disk health
python -c "
from ingestion.resource_manager import get_system_metrics, check_resource_health
metrics = get_system_metrics()
print(check_resource_health(metrics))
"

# Estimate resources needed for the pipeline
python -c "
from ingestion.resource_manager import estimate_pipeline_resources
print(estimate_pipeline_resources(num_tickers=5, days_of_data=90))
"

# Run full resource check and save report to S3
python -c "
import os
from ingestion.resource_manager import run_resource_check
print(run_resource_check(os.getenv('AWS_BUCKET_NAME', 'my-bucket')))
"
```

## Troubleshooting

### Pipeline fails with ModuleNotFoundError
Set PYTHONPATH before running:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

### S3 upload fails with NoCredentialsError
Check your .env file has correct AWS credentials:
```bash
python scripts/validate_secrets.py
```

### PostgreSQL connection refused
Make sure Docker is running:
```bash
docker-compose up -d postgres
```

### dbt run fails with connection error
Check profiles.yml matches your .env variables

### Prophet installation fails
Install with conda instead:
```bash
conda install -c conda-forge prophet
```

## Frequently Asked Questions

### How do I add a new stock ticker?
1. Add ticker to TICKERS list in ingestion/config_manager.py
2. Run backfill script to load historical data
3. Run full pipeline to generate AI insights

### How do I change the forecast horizon?
Update FORECAST_DAYS in config_manager.py (default is 5 days)

### How do I adjust anomaly sensitivity?
Update ANOMALY_CONTAMINATION in config_manager.py (default 0.05 = 5%)

### How do I disable Slack alerts?
Leave SLACK_WEBHOOK_URL empty in .env file — alerts are optional

## ML Model Registry

```bash
# Register a model
python -c "from ingestion.model_registry import register_model; import os; register_model('anomaly_detector', 'v1.0', {'contamination': 0.05}, {'precision': 0.92}, os.getenv('AWS_BUCKET_NAME'))"

# Promote model to production
python -c "from ingestion.model_registry import promote_model; import os; promote_model('anomaly_detector', 'v1.0', os.getenv('AWS_BUCKET_NAME'), 'production')"
```

## Email Notifications Setup

1. Enable 2FA on your Gmail account
2. Generate an App Password at myaccount.google.com/apppasswords
3. Add to .env:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   REPORT_EMAIL_TO=your-email@gmail.com
   ```
4. Test with:
   ```bash
   python -c "from ingestion.email_notifier import send_alert_email; send_alert_email('TEST', 'Test alert', 'AAPL')"
   ```

## Caching

```bash
# Clear expired cache entries
python -c "from ingestion.cache_manager import clear_expired_cache; import os; print(clear_expired_cache(os.getenv('AWS_BUCKET_NAME')))"

# Run performance benchmark
python -c "from ingestion.performance_optimizer import run_performance_benchmark; print(run_performance_benchmark())"
```

## Data Governance

```bash
# Run full governance check
python -c "from ingestion.data_governance import run_governance_check; import os; print(run_governance_check(os.getenv('AWS_BUCKET_NAME')))"

# Run compliance check
python -c "from ingestion.compliance_checker import run_compliance_check; import os; print(run_compliance_check(os.getenv('AWS_BUCKET_NAME')))"
```

## Data Lineage

```bash
# Run lineage tracking for a ticker
python -c "from ingestion.lineage_tracker import run_lineage_tracking; import os; run_lineage_tracking('AAPL', os.getenv('AWS_BUCKET_NAME'))"

# Get lineage for a dataset
python -c "from ingestion.lineage_tracker import get_dataset_lineage; import os; print(get_dataset_lineage('raw_prices', os.getenv('AWS_BUCKET_NAME')))"

# Run impact analysis
python -c "from ingestion.impact_analyzer import run_impact_analysis; import os, datetime; print(run_impact_analysis(os.getenv('AWS_BUCKET_NAME'), datetime.datetime.now().strftime('%Y/%m/%d')))"

# Analyze schema change impact
python -c "from ingestion.impact_analyzer import analyze_schema_change_impact; import os; print(analyze_schema_change_impact('raw_prices', ['volume', 'open'], os.getenv('AWS_BUCKET_NAME')))"
```

## Testing Strategy
```bash
# Run all tests (unit + integration + e2e)
pytest tests/ tests/integration/ tests/e2e/ -v

# Run only unit tests
pytest tests/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run only e2e tests
pytest tests/e2e/ -v

# Run with coverage report
pytest tests/ tests/integration/ tests/e2e/ --cov=ingestion --cov-report=html

# Run specific test file
pytest tests/test_anomaly_detector.py -v
```

# Generate compliance report
python -c "from ingestion.data_governance import generate_compliance_report; import os; print(generate_compliance_report(os.getenv('AWS_BUCKET_NAME')))"
```

## Data Quality Scoring

```bash
# Score all tickers for today
python -c "from ingestion.quality_scorer import run_quality_scoring; import os, datetime; print(run_quality_scoring(os.getenv('AWS_BUCKET_NAME'), datetime.datetime.now().strftime('%Y-%m-%d')))"

# Run automated test suite
python -c "from ingestion.test_framework import run_test_suite; import os, datetime; print(run_test_suite(os.getenv('AWS_BUCKET_NAME'), datetime.datetime.now().strftime('%Y-%m-%d')))"
```

## ML Model Explainability

```bash
# Run ensemble prediction for a ticker
python -c "from ingestion.ensemble_model import run_ensemble_prediction; import os; print(run_ensemble_prediction('AAPL', os.getenv('AWS_BUCKET_NAME')))"

# Get model explanation
python -c "from ingestion.model_explainer import run_model_explanation; import os; print(run_model_explanation('AAPL', os.getenv('AWS_BUCKET_NAME')))"
```

## Chaos Engineering

```bash
# Enable chaos mode (use with caution!)
export CHAOS_ENABLED=true

# Run chaos report for today
python -c "from ingestion.chaos_engineer import run_chaos_report; import os, datetime; print(run_chaos_report(os.getenv('AWS_BUCKET_NAME'), datetime.datetime.now().strftime('%Y/%m/%d')))"

# Run full stress test
python -c "from ingestion.stress_tester import run_full_stress_test; import os; print(run_full_stress_test(os.getenv('AWS_BUCKET_NAME')))"
```

## Warning
Never enable `CHAOS_ENABLED=true` in production without a rollback plan!

## Security

```bash
# Scan codebase for hardcoded secrets
python -c "from ingestion.security_scanner import run_security_scan; import os; print(run_security_scan('ingestion/', os.getenv('AWS_BUCKET_NAME')))"

# List all stored secrets (names only)
python -c "from ingestion.secrets_manager import list_secrets; import os; print(list_secrets(os.getenv('AWS_BUCKET_NAME')))"

# Store a new secret
python -c "from ingestion.secrets_manager import store_secret; import os; store_secret('my_api_key', 'value', os.getenv('AWS_BUCKET_NAME'))"
```

## Security Best Practices
- Never commit .env files
- Run security scanner before every PR
- Rotate secrets every 90 days
- Check audit logs monthly

## Property-Based Testing

```bash
# Run all property tests
python -c "from ingestion.property_tester import run_all_property_tests; import os; print(run_all_property_tests(os.getenv('AWS_BUCKET_NAME')))"

# Run mutation analysis on ingestion folder
python -c "from ingestion.mutation_analyzer import run_mutation_analysis; print(run_mutation_analysis('ingestion/'))"

# Generate edge case events
python -c "from ingestion.property_tester import generate_edge_case_events; import json; print(json.dumps(generate_edge_case_events(), indent=2))"
```

## Workflow Management

```bash
# Check which workflows are due now
python -c "from ingestion.workflow_manager import run_workflow_check; import os; print(run_workflow_check(os.getenv('AWS_BUCKET_NAME')))"

# Get workflow history for last 7 days
python -c "from ingestion.workflow_manager import get_workflow_history; import os; print(get_workflow_history('W001', os.getenv('AWS_BUCKET_NAME')))"

# Create a custom schedule
python -c "from ingestion.pipeline_scheduler import create_schedule; import os; create_schedule('my_schedule', '0 9 * * 1-5', ['fetch', 'validate'], os.getenv('AWS_BUCKET_NAME'))"

# Check next run time
python -c "from ingestion.pipeline_scheduler import get_next_run_time; from datetime import datetime; print(get_next_run_time('0 6 * * 1-5', datetime.now()))"
```

## Business Intelligence

```bash
# Run full BI analysis for all tickers
python -c "from ingestion.business_intelligence import run_bi_analysis; import os; print(run_bi_analysis(os.getenv('AWS_BUCKET_NAME')))"

# Get KPI dashboard
python -c "from ingestion.kpi_tracker import run_kpi_tracking; import os; print(run_kpi_tracking(os.getenv('AWS_BUCKET_NAME')))"

# Calculate Sharpe ratio manually
python -c "from ingestion.business_intelligence import calculate_sharpe_ratio; print(calculate_sharpe_ratio([0.01, 0.02, -0.005, 0.015, 0.008]))"
```

## Key Financial Metrics
- Sharpe Ratio > 1.0 = good risk-adjusted return
- Max Drawdown < -20% = high risk portfolio
- Market-cap weighted index mirrors S&P 500 methodology

## ML Model Serving

```bash
# Check all models are registered
python ingestion/model_server.py

# Check feature store
python -c "from ingestion.feature_store import run_feature_store_check; import os; print(run_feature_store_check(os.getenv('AWS_BUCKET_NAME')))"

# Get serving stats
python -c "from ingestion.model_server import get_model_serving_stats; import os, datetime; print(get_model_serving_stats(os.getenv('AWS_BUCKET_NAME'), datetime.datetime.now().strftime('%Y/%m/%d')))"
```

## Incremental Loading

```bash
# Run incremental load for all tickers
python -c "from ingestion.incremental_loader import run_incremental_load; import os; print(run_incremental_load(['AAPL','MSFT','GOOGL','AMZN','TSLA'], os.getenv('AWS_BUCKET_NAME')))"

# Check last loaded date for a ticker
python -c "from ingestion.incremental_loader import get_last_loaded_date; import os; print(get_last_loaded_date('AAPL', os.getenv('AWS_BUCKET_NAME')))"
```

## Data Versioning

```bash
# List all versions for a ticker
python -c "from ingestion.data_versioner import list_versions; import os, datetime; print(list_versions('AAPL', 'prices', os.getenv('AWS_BUCKET_NAME'), datetime.datetime.now().strftime('%Y/%m/%d')))"

# Compare two versions
python -c "from ingestion.data_versioner import compare_versions; import os, datetime; print(compare_versions('AAPL', 'prices', 'v1id1234', 'v2id5678', os.getenv('AWS_BUCKET_NAME'), datetime.datetime.now().strftime('%Y/%m/%d')))"
```

## Model Drift Detection

```bash
# Run drift detection for a ticker
python -c "from ingestion.drift_detector import run_drift_detection; import os; print(run_drift_detection('AAPL', os.getenv('AWS_BUCKET_NAME')))"

# Check retraining schedule
python -c "from ingestion.retraining_trigger import check_retraining_schedule; import os; print(check_retraining_schedule('anomaly_detector', os.getenv('AWS_BUCKET_NAME')))"

# Run full retraining check across all tickers
python -c "from ingestion.retraining_trigger import run_retraining_check; import os; print(run_retraining_check(['AAPL','MSFT','GOOGL','AMZN','TSLA'], os.getenv('AWS_BUCKET_NAME')))"
```

## Streamlit Dashboard

```bash
# Run dashboard locally (requires PostgreSQL running)
streamlit run dashboard/app.py --server.port=8503

# Run via Docker Compose
docker compose up stock-dashboard

# Run dashboard tests
pytest tests/test_dashboard.py -v

# Build dashboard Docker image manually
docker build -f dashboard/Dockerfile -t stock-dashboard .

# Open dashboard
open http://localhost:8503
```

## Model Monitoring

```bash
# Run model monitoring for a ticker
python -c "from ingestion.model_monitor import run_model_monitoring; import os; print(run_model_monitoring('AAPL', os.getenv('AWS_BUCKET_NAME')))"
```

## A/B Testing

```bash
# Create a new A/B experiment
python -c "from ingestion.ab_tester import create_ab_experiment; import os; print(create_ab_experiment('prophet_vs_ensemble', 'prophet', 'ensemble', 0.5, os.getenv('AWS_BUCKET_NAME')))"

# Analyze A/B results
python -c "from ingestion.ab_tester import analyze_ab_results; import os; print(analyze_ab_results('exp_id_here', os.getenv('AWS_BUCKET_NAME')))"

# Conclude experiment
python -c "from ingestion.ab_tester import conclude_experiment; import os; print(conclude_experiment('exp_id_here', os.getenv('AWS_BUCKET_NAME')))"
```

## Slack Integration Setup
1. Go to https://api.slack.com/apps
2. Create a new app → From scratch
3. Add Incoming Webhooks feature
4. Create webhook for your channel
5. Copy webhook URL to .env:
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

## Test Slack Integration

```bash
# Send test message
python -c "from ingestion.slack_alerter import send_slack_message; print(send_slack_message('Test from stock pipeline!', 'good', 'Test Alert'))"

# Send test anomaly alert
python -c "from ingestion.slack_alerter import alert_anomaly_detected; print(alert_anomaly_detected('AAPL', 'SPIKE', 185.50, -0.45, '2026-07-04'))"

# Send daily summary
python -c "from ingestion.slack_alerter import send_daily_summary; print(send_daily_summary(5, 2, 5, 92.5))"
```

## Configuration Management
```bash
# Validate all secrets before running pipeline
python scripts/validate_secrets.py

# Get config summary (no secrets exposed)
python -c "from ingestion.config_manager import get_config_summary; print(get_config_summary())"

# Check which configs are valid
python -c "from ingestion.config_manager import validate_all_configs; print(validate_all_configs())"
```

## Required Environment Variables
```
AWS:
  AWS_ACCESS_KEY_ID=your-key
  AWS_SECRET_ACCESS_KEY=your-secret
  AWS_BUCKET_NAME=your-bucket
  AWS_REGION=us-east-1

PostgreSQL:
  POSTGRES_HOST=localhost
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=your-password
  POSTGRES_DB=stock_pipeline

Snowflake:
  SNOWFLAKE_ACCOUNT=your-account
  SNOWFLAKE_USER=your-user
  SNOWFLAKE_PASSWORD=your-password
```

## Optional Environment Variables
```
OPENAI_API_KEY=your-key
SLACK_WEBHOOK_URL=your-webhook
NEWS_API_KEY=your-key
SMTP_HOST=smtp.gmail.com
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

## Quality Gates
```python
# Run quality gate check for a ticker
from ingestion.quality_gate import run_pipeline_gate_check
import os
metrics = {
    'hours_since_update': 10,
    'completeness_pct': 95.0,
    'quality_score': 88.0,
    'anomaly_rate_pct': 5.0,
    'prediction_accuracy_pct': 75.0
}
print(run_pipeline_gate_check('AAPL', metrics, os.getenv('AWS_BUCKET_NAME')))
```

## Auto Remediation
```python
# Run auto remediation check
from ingestion.auto_remediation import run_auto_remediation
import os
metrics = {'hours_since_update': 30, 'completeness_pct': 95.0}
print(run_auto_remediation('AAPL', metrics, os.getenv('AWS_BUCKET_NAME')))
```

## Pipeline Health Dashboard
```bash
# Generate health dashboard
python -c "from ingestion.pipeline_health_dashboard import run_health_dashboard_update; import os; print(run_health_dashboard_update(os.getenv('AWS_BUCKET_NAME')))"

# View dashboard URL
# Open the returned S3 URL in your browser
# Or download: aws s3 cp s3://bucket/reports/health_dashboard/YYYY/MM/DD/dashboard.html ./dashboard.html
```

## Data Discovery
```bash
# Discover all S3 datasets
python -c "from ingestion.data_discovery import run_data_discovery; import os; print(run_data_discovery(os.getenv('AWS_BUCKET_NAME')))"

# Search for specific datasets
python -c "from ingestion.data_discovery import search_datasets; import os; print(search_datasets(os.getenv('AWS_BUCKET_NAME'), 'anomalies'))"

# Profile a specific dataset
python -c "from ingestion.data_discovery import profile_dataset; import os; print(profile_dataset(os.getenv('AWS_BUCKET_NAME'), 'raw/stocks/'))"
```

## Real-Time Monitoring
```bash
# Run one monitor cycle
python -c "from ingestion.realtime_monitor import run_monitor_cycle; import os; print(run_monitor_cycle(os.getenv('AWS_BUCKET_NAME')))"

# Check API availability for a ticker
python -c "from ingestion.realtime_monitor import check_api_availability; print(check_api_availability('AAPL'))"

# Check pipeline lag
python -c "from ingestion.realtime_monitor import check_pipeline_lag; import os; print(check_pipeline_lag(os.getenv('AWS_BUCKET_NAME'), 'AAPL'))"
```

## SLA Reporting
```bash
# Generate SLA report for today
python -c "from ingestion.sla_reporter import run_sla_reporting; import os; print(run_sla_reporting(os.getenv('AWS_BUCKET_NAME')))"

# Get 30-day SLA trend
python -c "from ingestion.sla_reporter import get_sla_trend; import os; print(get_sla_trend(os.getenv('AWS_BUCKET_NAME')))"
```

## Feature Flags
```bash
# Check if a feature is enabled
python -c "from ingestion.feature_flag_manager import is_enabled; import os; print(is_enabled('enable_gpt_insights', os.getenv('AWS_BUCKET_NAME')))"

# Enable a feature
python -c "from ingestion.feature_flag_manager import enable_flag; import os; enable_flag('enable_kafka_streaming', os.getenv('AWS_BUCKET_NAME'))"

# Disable a feature
python -c "from ingestion.feature_flag_manager import disable_flag; import os; disable_flag('enable_chaos_engineering', os.getenv('AWS_BUCKET_NAME'))"

# Run flag audit
python -c "from ingestion.feature_flag_manager import run_flag_audit; import os; print(run_flag_audit(os.getenv('AWS_BUCKET_NAME')))"
```

## Default Feature Flags
| Flag | Default | Description |
|---|---|---|
| enable_gpt_insights | True | GPT market summaries |
| enable_kafka_streaming | False | Real-time Kafka layer |
| enable_chaos_engineering | False | Chaos scenarios |
| enable_ensemble_models | True | RF+GB+Linear ensemble |
| enable_news_sentiment | True | News sentiment analysis |
| enable_slack_alerts | True | Slack notifications |
| enable_snowflake_sync | True | Snowflake warehouse sync |
| enable_auto_remediation | True | Auto fix pipeline issues |
| enable_ab_testing | False | A/B model testing |

## Data Mesh

```bash
# Register all data products
python -c "from ingestion.data_product_manager import run_data_mesh_registration; import os; run_data_mesh_registration(os.getenv('AWS_BUCKET_NAME'))"

# List all data products
python -c "from ingestion.data_product_manager import list_data_products; import os; print(list_data_products(os.getenv('AWS_BUCKET_NAME')))"

# Get domain summary
python -c "from ingestion.data_product_manager import get_domain_summary; import os; print(get_domain_summary(os.getenv('AWS_BUCKET_NAME')))"
```

## Event Bus

```bash
# Publish a pipeline completed event
python -c "from ingestion.event_bus import publish_pipeline_completed; import os; print(publish_pipeline_completed('AAPL', 45.5, os.getenv('AWS_BUCKET_NAME')))"

# Get event summary for today
python -c "from ingestion.event_bus import get_event_summary; import os, datetime; print(get_event_summary(os.getenv('AWS_BUCKET_NAME'), datetime.datetime.now().strftime('%Y/%m/%d')))"
```

## Data Contracts

```bash
# Register all contracts
python -c "from ingestion.data_contract_manager import run_contract_registration; import os; run_contract_registration(os.getenv('AWS_BUCKET_NAME'))"

# Validate data against contract
python -c "
from ingestion.data_contract_manager import validate_against_contract, STOCK_PRICE_CONTRACT
data = {'ticker': 'AAPL', 'trade_date': '2026-07-14', 'open_price': 185.0,
        'high_price': 190.0, 'low_price': 183.0, 'close_price': 188.0, 'volume': 1000000}
print(validate_against_contract(data, STOCK_PRICE_CONTRACT))
"
```

## Schema Registry

```bash
# Set up schema registry
python -c "from ingestion.schema_registry import run_schema_registry_setup; import os; run_schema_registry_setup(os.getenv('AWS_BUCKET_NAME'))"

# Get latest schema
python -c "from ingestion.schema_registry import get_latest_schema; import os; print(get_latest_schema('stock_prices_raw', os.getenv('AWS_BUCKET_NAME')))"

# List all schemas
python -c "from ingestion.schema_registry import list_schemas; import os; print(list_schemas(os.getenv('AWS_BUCKET_NAME')))"
```

## Data Privacy and PII Management

```bash
# Scan a prefix for PII
python -c "from ingestion.pii_detector import run_pii_scan; import os; print(run_pii_scan(os.getenv('AWS_BUCKET_NAME'), 'raw/stocks/'))"

# Check if stock data has PII
python -c "
from ingestion.pii_detector import scan_for_pii
data = {'ticker': 'AAPL', 'close_price': 185.0, 'volume': 1000000}
print(scan_for_pii(data))
"

# Run full privacy check
python -c "from ingestion.data_privacy_manager import run_privacy_check; import os; print(run_privacy_check(os.getenv('AWS_BUCKET_NAME')))"

# Check policy compliance for a dataset
python -c "
from ingestion.data_privacy_manager import check_policy_compliance
metadata = {'classification': 'CONFIDENTIAL', 'retention_days': 365, 'has_pii': False}
print(check_policy_compliance('financial_data', metadata))
"
```

## Privacy Policies
| Policy | Classification | Retention | PII Allowed |
|---|---|---|---|
| financial_data | CONFIDENTIAL | 365 days | ❌ No |
| ml_features | INTERNAL | 90 days | ❌ No |
| audit_logs | CONFIDENTIAL | 730 days | ❌ No |
| cache_data | PUBLIC | 7 days | ❌ No |

## Data Archival and Cold Storage

```bash
# Preview archival candidates (dry-run, no changes made)
python -c "from ingestion.data_archiver import run_archival_pipeline; import os; print(run_archival_pipeline(os.getenv('AWS_BUCKET_NAME'), dry_run=True))"

# Check archive candidates for a specific prefix
python -c "
from ingestion.data_archiver import identify_archive_candidates
import os
candidates = identify_archive_candidates(os.getenv('AWS_BUCKET_NAME'), 'raw/stocks', 90)
print(f'Objects to archive: {len(candidates)}')
"

# Preview deletion candidates
python -c "
from ingestion.data_archiver import identify_deletion_candidates
import os
expired = identify_deletion_candidates(os.getenv('AWS_BUCKET_NAME'), 'raw/stocks', 365)
print(f'Objects to delete: {len(expired)}')
"
```

## Storage Tier Management

```bash
# Get recommended tier changes for a prefix
python -c "
from ingestion.storage_tier_manager import recommend_tier_changes
import os
recs = recommend_tier_changes(os.getenv('AWS_BUCKET_NAME'), 'raw/stocks')
print(f'Tier changes recommended: {len(recs)}')
"

# Check current tier of an object
python -c "
from ingestion.storage_tier_manager import get_object_tier
import os
info = get_object_tier(os.getenv('AWS_BUCKET_NAME'), 'raw/stocks/2024/01/01/AAPL/prices.json')
print(f\"Tier: {info['tier']} | Age: {info['age_days']} days\")
"

# Run tier optimization (dry-run)
python -c "from ingestion.storage_tier_manager import run_tier_optimization; import os; print(run_tier_optimization(os.getenv('AWS_BUCKET_NAME'), 'raw/stocks', dry_run=True))"
```

## Storage Tiers Reference
| Tier   | S3 Class     | Cost/GB    | Min Age  |
|--------|--------------|------------|----------|
| HOT    | STANDARD     | $0.023     | 0 days   |
| WARM   | STANDARD_IA  | $0.0125    | 30 days  |
| COLD   | GLACIER      | $0.004     | 90 days  |
| FROZEN | DEEP_ARCHIVE | $0.00099   | 180 days |

## API Testing Commands

### Start All APIs
```bash
# Terminal 1: REST API
uvicorn api.main:app --reload --port 8000

# Terminal 2: GraphQL API
uvicorn api.graphql_api:app --reload --port 8001

# Terminal 3: WebSocket API
uvicorn api.websocket_server:app --reload --port 8002
```

### Test REST Endpoints with curl
```bash
# Health check
curl http://localhost:8000/health

# Get prices
curl "http://localhost:8000/prices/AAPL?days=7"

# Get anomalies
curl http://localhost:8000/anomalies/AAPL

# Get pipeline health
curl http://localhost:8000/pipeline-health

# Get feature flags
curl http://localhost:8000/feature-flags

# Get data products
curl http://localhost:8000/data-products

# Get event summary
curl http://localhost:8000/events/summary

# Scan for PII
curl "http://localhost:8000/privacy-scan/raw/stocks"

# API documentation
curl http://localhost:8000/api-docs/summary
curl http://localhost:8000/api-docs/endpoints/ml
```

### Test GraphQL
```bash
curl -X POST http://localhost:8001/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ tickers }"}'
```

### Test WebSocket (Python)
```python
import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://localhost:8002/ws/prices') as ws:
        msg = await ws.recv()
        print(json.loads(msg))

asyncio.run(test())
```

## Test Coverage

```bash
# Run tests with coverage report
pytest tests/ --cov=ingestion --cov-report=html --cov-report=term-missing

# View HTML coverage report
start htmlcov/index.html  # Windows
```

```python
# Run coverage check module
from ingestion.test_coverage_reporter import run_coverage_check
import os
print(run_coverage_check(os.getenv('AWS_BUCKET_NAME')))
```

```python
# Find low coverage files
from ingestion.test_coverage_reporter import get_low_coverage_files
coverage_data = {'total_coverage_pct': 85.0, 'files': {
    'ingestion/fetch_stocks.py': {'coverage_pct': 75.0, 'missing_lines': 5},
    'ingestion/anomaly_detector.py': {'coverage_pct': 90.0, 'missing_lines': 2}
}}
print(get_low_coverage_files(coverage_data, threshold_pct=80.0))
```

## Performance Benchmarks

```bash
# Run full benchmark suite
python -c "from ingestion.performance_benchmarker import run_benchmark_suite; import os; print(run_benchmark_suite(os.getenv('AWS_BUCKET_NAME')))"
```

```python
# Benchmark a specific operation
from ingestion.performance_benchmarker import benchmark_function
import time
result = benchmark_function(lambda: time.sleep(0.01), runs=10)
print('Avg ms:', result['avg_ms'])
```

## AutoML Pipeline
```bash
# Run AutoML for a ticker
python -c "from ingestion.automl_pipeline import run_automl_pipeline; import os; print(run_automl_pipeline('AAPL', os.getenv('AWS_BUCKET_NAME')))"
```

## Hyperparameter Tuning
```bash
# Tune Random Forest for a ticker
python -c "from ingestion.hyperparameter_tuner import run_hyperparameter_tuning; import os; print(run_hyperparameter_tuning('AAPL', os.getenv('AWS_BUCKET_NAME')))"
```

## AutoML Candidate Models
| Model | Type | Key Params |
|---|---|---|
| random_forest | Tree ensemble | n_estimators=100, max_depth=10 |
| gradient_boosting | Boosting | n_estimators=100, lr=0.1 |
| linear_regression | Linear | no params |
| ridge | Regularized linear | alpha=1.0 |
| lasso | Sparse linear | alpha=1.0 |

## Hyperparameter Grid
Random Forest:
- n_estimators: [50, 100, 200]
- max_depth: [5, 10, None]
- min_samples_split: [2, 5, 10]
Total combinations: 27

## Streaming Analytics
```bash
# Process a price stream with sliding windows
python -c "
from ingestion.streaming_analytics import process_price_stream
import os
prices = [185.0, 186.2, 184.8, 187.5, 185.1, 188.0, 184.5, 189.2, 186.8, 190.0]
result = process_price_stream('AAPL', prices, window_size=5)
print('Processed:', result['processed'])
print('Anomalies:', result['anomalies'])
"
```

## Real-Time Aggregation
```bash
# Aggregate prices into OHLCV bars
python -c "
from ingestion.realtime_aggregator import aggregate_ohlcv
import datetime
prices = [
    {'price': 185.0, 'volume': 1000, 'timestamp': '2026-07-18T09:30:00'},
    {'price': 186.0, 'volume': 1500, 'timestamp': '2026-07-18T09:32:00'},
    {'price': 184.5, 'volume': 800, 'timestamp': '2026-07-18T09:35:00'},
]
bars = aggregate_ohlcv(prices, window_minutes=5)
print('OHLCV bars:', len(bars))
"

# Calculate VWAP
python -c "
from ingestion.realtime_aggregator import calculate_vwap
prices = [
    {'price': 185.0, 'volume': 1000},
    {'price': 186.0, 'volume': 2000},
    {'price': 184.0, 'volume': 500},
]
print('VWAP:', calculate_vwap(prices))
"

# Detect momentum
python -c "
from ingestion.realtime_aggregator import detect_momentum
prices = [180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200]
print(detect_momentum(prices, short_period=5, long_period=20))
"
```

## Distributed Processing
```bash
# Run parallel ticker processing
python -c "
from ingestion.distributed_task_manager import run_parallel_ticker_processing
import os

def process_ticker(ticker, bucket=''):
    return {'ticker': ticker, 'processed': True}

result = run_parallel_ticker_processing(
    ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
    process_ticker,
    max_workers=5
)
print('Success:', result['success_count'])
print('Total time:', result['total_seconds'], 'seconds')
"
```

## Pipeline Optimization
```bash
# Run pipeline profiling
python -c "from ingestion.pipeline_optimizer import run_pipeline_profiling; import os; print(run_pipeline_profiling(os.getenv('AWS_BUCKET_NAME')))"

# Check for bottlenecks
python -c "
from ingestion.pipeline_optimizer import identify_bottlenecks
profiles = [
    {'step': 'fetch_stocks', 'duration_seconds': 15.2},
    {'step': 'validate', 'duration_seconds': 2.1},
    {'step': 'anomaly_detect', 'duration_seconds': 8.5},
]
bottlenecks = identify_bottlenecks(profiles, threshold_seconds=10.0)
print('Bottlenecks:', [b['step'] for b in bottlenecks])
"
```

## NLP Processing
```bash
# Analyze financial text
python -c "
from ingestion.nlp_processor import calculate_text_sentiment
text = 'Apple delivered a strong earnings beat with bullish guidance and upgraded price targets.'
result = calculate_text_sentiment(text)
print('Sentiment:', result['label'])
print('Score:', result['score'])
"

# Extract financial entities
python -c "
from ingestion.nlp_processor import extract_financial_entities
text = 'AAPL surged 5.2% to \$188.50 after beating earnings estimates.'
entities = extract_financial_entities(text)
print('Tickers:', entities['tickers'])
print('Amounts:', entities['amounts'])
print('Percentages:', entities['percentages'])
"
```

## Text Analytics
```bash
# Classify news category
python -c "
from ingestion.text_analytics import classify_news_category
text = 'Apple reported Q3 earnings with revenue beating Wall Street estimates.'
print('Category:', classify_news_category(text))
"

# Extract price targets
python -c "
from ingestion.text_analytics import extract_price_targets
text = 'Goldman Sachs raised its price target to \$200 for Apple stock.'
print('Targets:', extract_price_targets(text))
"
```

## Time Series Analysis
```bash
# Run full time series analysis for a ticker
python -c "
from ingestion.timeseries_analyzer import run_timeseries_analysis
import os
prices = [180+i*0.5 + (i%5)*0.3 for i in range(60)]
result = run_timeseries_analysis('AAPL', prices, os.getenv('AWS_BUCKET_NAME'))
print('Trend:', result.get('trend', {}).get('trend'))
print('Volatility regime:', result.get('volatility', {}).get('regime'))
"

# Detect trend
python -c "
from ingestion.timeseries_analyzer import detect_trend
prices = [180+i*0.5 for i in range(30)]
print(detect_trend(prices))
"
```

## Forecast Enhancement
```bash
# Generate scenario forecasts
python -c "
from ingestion.forecast_enhancer import generate_scenario_forecasts
scenarios = generate_scenario_forecasts(base_prediction=185.0, volatility=3.5)
print('Bull:', scenarios['bull'])
print('Base:', scenarios['base'])
print('Bear:', scenarios['bear'])
"

# Blend Prophet and Ensemble predictions
python -c "
from ingestion.forecast_enhancer import blend_forecasts
prophet = [185.0, 186.0, 187.0, 188.0, 189.0]
ensemble = [183.0, 184.0, 185.0, 186.0, 187.0]
blended = blend_forecasts(prophet, ensemble, prophet_weight=0.6)
print('Blended predictions:', blended)
"

# Calculate forecast accuracy
python -c "
from ingestion.forecast_enhancer import calculate_forecast_accuracy
predictions = [185.0, 186.0, 184.0, 187.0, 185.5]
actuals = [186.0, 185.5, 184.5, 188.0, 185.0]
accuracy = calculate_forecast_accuracy(predictions, actuals)
print('MAE:', accuracy['MAE'])
print('RMSE:', accuracy['RMSE'])
print('Directional accuracy:', accuracy['directional_accuracy'])
"
```

## Market Graph Analysis
```bash
# Run market graph analysis
python -c "
from ingestion.market_graph_analyzer import run_market_graph_analysis
import os
ticker_prices = {
    'AAPL': [185+i*0.1 for i in range(30)],
    'MSFT': [415+i*0.2 for i in range(30)],
    'GOOGL': [175+i*0.15 for i in range(30)],
    'AMZN': [195+i*0.05 for i in range(30)],
    'TSLA': [250+i*0.3 for i in range(30)],
}
result = run_market_graph_analysis(ticker_prices, os.getenv('AWS_BUCKET_NAME'))
print('Market leader:', result.get('leader'))
print('Risk level:', result.get('stability', {}).get('risk_level'))
"
```

## Sector Analysis
```bash
# Run sector analysis
python -c "
from ingestion.sector_analyzer import run_sector_analysis
import os
ticker_prices = {
    'AAPL': [185+i*0.1 for i in range(30)],
    'MSFT': [415+i*0.2 for i in range(30)],
    'GOOGL': [175+i*0.15 for i in range(30)],
    'AMZN': [195+i*0.05 for i in range(30)],
    'TSLA': [250+i*0.3 for i in range(30)],
}
result = run_sector_analysis(ticker_prices, os.getenv('AWS_BUCKET_NAME'))
print('Sector returns:', result.get('sector_returns'))
print('Leaders:', result.get('sector_leaders'))
"
```
