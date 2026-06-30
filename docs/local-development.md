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
# Archive old raw data (keeps last 30 days)
python -c "from ingestion.s3_optimizer import run_s3_optimization; run_s3_optimization()"

# Check monthly S3 cost estimate
python -c "from ingestion.s3_optimizer import generate_cost_report; import os; print(generate_cost_report(os.getenv('AWS_BUCKET_NAME')))"
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
