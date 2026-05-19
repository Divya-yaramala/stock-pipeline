# Stock Price Data Pipeline

An AI-powered stock price pipeline that ingests daily prices, detects anomalies with ML, predicts next-day closing prices, and generates LLM-powered market insights — storing raw data in AWS S3, transforming with dbt, warehousing in Snowflake, and orchestrated end-to-end by Apache Airflow.

---

## Architecture

```
  ┌─────────────┐     ┌─────────┐     ┌──────────┐     ┌─────┐     ┌───────────┐
  │  Yahoo      │────▶│  AWS S3 │────▶│ Postgres │────▶│ dbt │────▶│ Snowflake │
  │  Finance API│     │  (Raw)  │     │ (Staging)│     │     │     │ (Marts)   │
  └─────────────┘     └─────────┘     └──────────┘     └─────┘     └───────────┘
         │                                                                │
         └──────────────────── Apache Airflow (Orchestration) ───────────┘
```

---

## Tech Stack

| Layer           | Tool / Service            |
|-----------------|---------------------------|
| Orchestration   | Apache Airflow 2.9        |
| Ingestion       | Python, yfinance          |
| Raw Storage     | AWS S3                    |
| Staging DB      | PostgreSQL (Docker)       |
| Transformation  | dbt                       |
| Data Warehouse  | Snowflake                 |
| Containerization| Docker + Docker Compose   |

---

## Getting Started

```bash
# 1. Copy environment variables and fill in your credentials
cp .env.example .env

# 2. Start all services (Postgres + Airflow)
docker-compose up -d

# 3. Check health of all services
python scripts/check_airflow.py

# 4. Open Airflow UI at http://localhost:8080  (admin / admin)

# Run full pipeline locally (without Airflow)
python scripts/run_pipeline_local.py
```

---

## Project Structure

```
stock-pipeline/
├── dags/               # Airflow DAG definitions
├── ingestion/          # Python scripts to fetch and upload stock data
├── dbt_project/
│   └── models/
│       ├── staging/    # Clean and cast raw data
│       └── marts/      # Analytics-ready aggregates
├── tests/              # pytest unit tests
├── docs/               # Architecture diagrams and notes
├── scripts/            # One-off utility scripts
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Author

**Divya Yaramala** — Data Engineer
- GitHub: [Divya-yaramala](https://github.com/Divya-yaramala)
- Email: divyayaramala145@gmail.com

---

## Current AI Pipeline

```
check_trading_day → fetch_and_upload_to_s3 → load_to_postgres_staging → run_dbt_models → run_anomaly_detection → run_price_prediction → run_market_insights → run_snowflake_sync
```

---

## Progress Log

### ✅ Day 1 — Project Scaffold
- Created complete folder structure
- Docker Compose with Postgres + Airflow
- .env.example with all required variables
- .gitignore covering Python, dbt, Airflow
- ASCII architecture diagram

### ✅ Day 2 — Ingestion Script
- Python ingestion script using yfinance
- Fetches OHLCV data for 5 tickers: AAPL, MSFT, GOOGL, AMZN, TSLA
- Uploads raw JSON to AWS S3 with date partitioning: raw/stocks/YYYY/MM/DD/
- Type hints and logging on every function
- 5 unit tests using pytest with mocked boto3 and yfinance
- All tests passing green

### ✅ Day 3 — AI Anomaly Detection
- Added Isolation Forest ML model to detect unusual stock price movements
- Detects anomalies across 5 features: open, high, low, close, volume
- Saves anomaly results to S3 under processed/anomalies/YYYY/MM/DD/
- 6 unit tests all passing green
- scikit-learn and numpy added to requirements.txt

### ✅ Day 4 — AI Price Prediction
- Built stock price prediction model using Facebook Prophet
- Predicts next 5 days closing prices for all 5 tickers
- Saves predictions to S3 under processed/predictions/YYYY/MM/DD/
- Wired into Airflow DAG as final task
- 7 unit tests all passing green
- Prophet added to requirements.txt

### ✅ Day 5 — LLM Market Insights
- Built GPT-powered market insight generator using OpenAI API
- Reads stock prices, anomaly results, and predictions for each ticker
- Generates a 3-sentence professional market summary per ticker daily
- Saves insights to S3 under processed/insights/YYYY/MM/DD/
- Wired into Airflow DAG as final task
- 7 unit tests all passing green
- openai added to requirements.txt

### ✅ Day 6 — PostgreSQL Staging Layer and dbt Models
- Created scripts/setup_postgres.py to initialise staging schema and 4 tables
- Tables: stock_prices_raw, stock_anomalies, stock_predictions, stock_insights
- All tables use UNIQUE(ticker, date) constraints with ON CONFLICT DO NOTHING
- Built 4 dbt models: stg_stock_prices, stg_stock_anomalies, fct_stock_prices, dim_tickers
- Staging models materialised as views; marts as tables
- schema.yml with not_null and unique data-quality tests
- 6 unit tests all passing green
- psycopg2-binary and dbt-postgres added to requirements.txt

### ✅ Day 8 — Docker and Airflow UI
- Fixed docker-compose.yml: postgres:15, updated airflow-init user details, scripts/ volume mount
- Created airflow-requirements.txt for pipeline dependencies inside containers
- Webserver and scheduler install requirements on startup via pip
- Created scripts/check_airflow.py — health checks for webserver, Postgres, and DAG syntax
- Getting Started section updated with health check command

### ✅ Day 9 — Snowflake Integration
- Created Snowflake setup script with database, schemas, warehouse, tables
- Added dbt Snowflake profile alongside existing Postgres profile
- Built Snowflake sync script to load all 4 data types from S3
- Wired Snowflake sync as final Airflow DAG task
- 6 unit tests passing green
- Updated requirements.txt with Snowflake dependencies

### ✅ Day 7 — End-to-End Pipeline Wiring
- Wired load_to_postgres_staging task in Airflow DAG with real implementation
- Created integration tests: full pipeline flow, S3 path consistency, idempotency
- Built scripts/run_pipeline_local.py with step timer and summary table
- Added local run command to Getting Started section
- 34/34 tests passing green
