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
