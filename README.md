# 🚀 AI-Powered Stock Price Pipeline

[![CI Pipeline](https://github.com/Divya-yaramala/stock-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Divya-yaramala/stock-pipeline/actions/workflows/ci.yml)
[![Code Quality](https://github.com/Divya-yaramala/stock-pipeline/actions/workflows/code-quality.yml/badge.svg)](https://github.com/Divya-yaramala/stock-pipeline/actions/workflows/code-quality.yml)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Tests](https://img.shields.io/badge/tests-108%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)
![Airflow](https://img.shields.io/badge/Airflow-2.9-red)
![dbt](https://img.shields.io/badge/dbt-Core-orange)
![Snowflake](https://img.shields.io/badge/Snowflake-blue)

---
> 🎉 **Phase 1-4 Complete!** 108 tests · 13 Airflow tasks · 6 dbt models · 7 ADRs · 10 production patterns · 25 days of building
---

> An end-to-end AI-powered data engineering pipeline that ingests daily stock prices, detects anomalies with ML, predicts future prices with Prophet, and generates LLM market insights — orchestrated by Apache Airflow, transformed with dbt, and warehoused in Snowflake.

---

## 🎬 Demo
> 📹 Loom walkthrough coming soon
>
> The video will cover: architecture overview, AI components, code quality, and production patterns.
>
> **Live stats:** 108 tests passing · 13 Airflow tasks · 6 dbt models · 7 ADRs

---

## 📐 Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         APACHE AIRFLOW (Orchestration)                       │
│                                                                              │
│  ┌─────────────┐   ┌──────────┐   ┌──────────┐   ┌────────────────────────┐│
│  │  Yahoo      │──▶│  AWS S3  │──▶│ Postgres │──▶│        dbt Core        ││
│  │  Finance API│   │ (Raw /   │   │(Staging) │   │  stg_stock_prices      ││
│  │  yfinance   │   │  errors/ │   │  4 tables│   │  stg_stock_anomalies   ││
│  └─────────────┘   │  archive)│   └────┬─────┘   │  fct_stock_prices      ││
│                    └──────────┘        │          │  dim_tickers           ││
│                         ▲             │          │  fct_daily_summary     ││
│                         │             │          └────────────┬───────────┘│
│              ┌──────────┴──────────┐  │                       │            │
│              │      AI Layer       │  │                       ▼            │
│              │                     │  │          ┌────────────────────────┐│
│              │ 🔍 Anomaly Detection│  │          │       Snowflake        ││
│              │  Isolation Forest   │  │          │   STOCK_DB.RAW         ││
│              │                     │  │          │   STOCK_DB.ANALYTICS   ││
│              │ 📈 Price Prediction │  │          └────────────────────────┘│
│              │  Facebook Prophet   │◀─┘                                    │
│              │  (5-day forecast)   │                                        │
│              │                     │                                        │
│              │ 💬 LLM Insights     │                                        │
│              │  GPT-3.5 Turbo      │                                        │
│              │  (daily summaries)  │                                        │
│              └─────────────────────┘                                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Project Stats
| Metric | Value |
|---|---|
| Total tests | 108 passing |
| Airflow tasks | 13 |
| dbt models | 6 |
| ADRs | 7 |
| Production patterns | 10 |
| Days to build | 25 |
| CI/CD workflows | 2 |

---

## ✨ Key Features

- 🤖 **AI Anomaly Detection** — Isolation Forest ML model flags unusual price/volume movements across 5 features
- 📈 **Price Prediction** — Facebook Prophet forecasts next 5 days of closing prices per ticker
- 💬 **LLM Market Insights** — GPT-3.5 generates daily professional market summaries
- 🔄 **Incremental Loading** — Automatically detects and backfills missing date gaps
- ✅ **Data Validation** — 7-point quality checks per ticker with configurable SLA alerting
- 🔔 **Slack Alerting** — Real-time pipeline notifications on success, failure, and SLA breaches
- 💰 **Cost Optimization** — S3 storage analysis, old-data archiving, and monthly cost estimation
- 🛡️ **Dead Letter Queue** — Failed records captured to S3 and replayed automatically
- 📊 **Pipeline Monitoring** — Per-step execution metrics and daily SLA compliance reports
- 🔍 **Data Lineage** — Full audit trail tracking every record from Yahoo Finance API to Snowflake

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | Apache Airflow 2.9 |
| Ingestion | Python 3.11 + yfinance |
| AI / ML | scikit-learn (Isolation Forest) + Prophet + OpenAI GPT-3.5 |
| Raw Storage | AWS S3 |
| Staging DB | PostgreSQL 15 (Docker) |
| Transformation | dbt Core |
| Data Warehouse | Snowflake |
| Alerting | Slack Webhooks |
| CI / CD | GitHub Actions |
| Testing | pytest — 108 tests |
| Code Quality | black + isort + flake8 + mypy |

---

## 🏗️ Pipeline DAG (13 Tasks)

```
check_trading_day
       │
       ▼
validate_data ──────────────────────────────────────────┐
       │                                                 │
       ▼                                                 │
fetch_and_upload_to_s3                                   │
       │                                                 │
       ▼                                                 │
load_to_postgres_staging                                 │
       │                                                 │
       ├──────────────────────────────────┐              │
       ▼                                  ▼              │
run_anomaly_detection           run_dbt_models           │
       │                                  │              │
       ▼                                  ▼              │
run_price_prediction            run_snowflake_sync       │
       │                                                 │
       ▼                                                 │
run_market_insights                                      │
       │                                                 │
       ▼                                                 │
run_quality_report ◀─────────────────────────────────────┘
       │
       ▼
run_monitoring_report
       │
       ▼
replay_dead_letter_queue
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Docker + Docker Compose
- AWS account with S3 bucket
- Snowflake account
- OpenAI API key
- Slack webhook URL (optional)

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Divya-yaramala/stock-pipeline.git
cd stock-pipeline

# 2. Copy environment variables and fill in your credentials
cp .env.example .env

# 3. Start all services (Postgres + Airflow)
docker-compose up -d

# 4. Validate all environment variables
python scripts/validate_secrets.py

# 5. Check health of all services
python scripts/check_airflow.py

# 6. Open Airflow UI at http://localhost:8080  (admin / admin)

# 7. Run full pipeline locally (without Airflow)
python scripts/run_pipeline_local.py
```

### Running Tests

```bash
# Run all 108 tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=ingestion

# Run a specific module
pytest tests/test_anomaly_detector.py -v
```

### Backfilling Missing Data

```bash
# Preview gaps without loading
python scripts/backfill_stocks.py --ticker AAPL --start-date 2024-01-01 --end-date 2024-01-31 --dry-run

# Load gaps for all tickers
python scripts/backfill_stocks.py --start-date 2024-01-01 --end-date 2024-01-31
```

### Rolling Back a Pipeline Step

```bash
# Rollback a pipeline step to a previous version
python scripts/rollback_pipeline.py --ticker AAPL --step fetch --version-id abc12345

# Preview rollback without executing
python scripts/rollback_pipeline.py --ticker AAPL --step fetch --version-id abc12345 --dry-run
```

---

## 🌐 REST API
The pipeline exposes a REST API for querying results:

| Endpoint | Description |
|---|---|
| GET /health | Health check |
| GET /tickers | List available tickers |
| GET /prices/{ticker} | Latest stock prices |
| GET /anomalies/{ticker} | Anomaly detection results |
| GET /predictions/{ticker} | Price predictions |
| GET /insights/{ticker} | LLM market insights |
| GET /summary/{ticker} | Combined summary |

Start the API:
```bash
# With Docker
docker-compose up -d stock-api
# Open http://localhost:8000/docs for Swagger UI

# Without Docker
uvicorn api.main:app --reload --port 8000
```

---

## 📁 Project Structure

```
stock-pipeline/
├── dags/
│   └── stock_price_pipeline.py     # Airflow DAG — 13-task daily pipeline
│
├── ingestion/
│   ├── fetch_stocks.py             # Yahoo Finance → S3 with date partitioning
│   ├── anomaly_detector.py         # Isolation Forest ML anomaly detection
│   ├── price_predictor.py          # Facebook Prophet 5-day price forecasting
│   ├── market_insights.py          # GPT-3.5 daily market summary generation
│   ├── data_validator.py           # 7-point data quality validation checks
│   ├── pipeline_monitor.py         # Per-step execution metrics tracking
│   ├── dead_letter_queue.py        # Failed record capture and replay
│   ├── slack_alerter.py            # Slack webhook notifications
│   ├── lineage_tracker.py          # End-to-end data lineage recording
│   ├── incremental_loader.py       # Gap detection and automatic backfill
│   ├── quality_reporter.py         # Ticker-level quality scoring (0–100%)
│   ├── sla_monitor.py              # SLA compliance tracking and alerting
│   ├── s3_optimizer.py             # S3 cost analysis and archiving
│   ├── resource_manager.py         # CPU/memory/disk resource gate
│   ├── snowflake_sync.py           # Snowflake bulk load from S3
│   └── config_manager.py           # Typed config via Python dataclasses
│
├── dbt_project/
│   └── models/
│       ├── staging/                # stg_stock_prices, stg_stock_anomalies
│       └── marts/                  # fct_stock_prices, dim_tickers,
│                                   # fct_daily_summary, fct_anomaly_summary
│
├── tests/                          # pytest — 108 unit tests
├── docs/
│   ├── pipeline-overview.md        # Data flow, components, scheduling
│   ├── local-development.md        # Setup, common errors, adding tickers
│   ├── data-dictionary.md          # All tables and columns documented
│   └── adr/                        # 7 Architecture Decision Records
│
├── scripts/
│   ├── run_pipeline_local.py       # Full local pipeline run with timing
│   ├── backfill_stocks.py          # CLI backfill with --dry-run support
│   ├── validate_secrets.py         # Pre-flight env var validation
│   └── check_airflow.py            # Service health checks
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Run 108 tests on every push
│       └── code-quality.yml        # black, isort, flake8, mypy checks
│
├── docker-compose.yml              # Postgres + Airflow services
├── .env.example                    # All required environment variables
├── requirements.txt                # Python dependencies
└── pyproject.toml                  # black, isort, mypy configuration
```

---

## 📚 Documentation

| Document | Description |
|---|---|
| [Pipeline Overview](docs/pipeline-overview.md) | Data flow, components, AI layer, scheduling |
| [Local Development Guide](docs/local-development.md) | Setup steps, common errors, adding tickers |
| [Data Dictionary](docs/data-dictionary.md) | All tables and columns across Postgres, Snowflake, dbt |
| [Architecture Decision Records](docs/adr/README.md) | Technology choices with rationale |
| [Portfolio Summary](docs/portfolio-summary.md) | Skills, projects, and availability |
| [Loom Video Script](docs/loom-video-script.md) | 3-minute walkthrough script and recording checklist |
| [Project Checklist](docs/project-checklist.md) | 90-day completion checklist with code quality, docs, production patterns |
| [REST API Documentation](docs/api-docs.md) | Endpoint reference, request/response examples, Swagger UI guide |

---

## 🏛️ Architecture Decisions

| # | Decision | Status |
|---|---|---|
| ADR-001 | [Why Airflow over Prefect](docs/adr/001-why-airflow-over-prefect.md) | Accepted |
| ADR-002 | [Why Snowflake over Redshift](docs/adr/002-why-snowflake-over-redshift.md) | Accepted |
| ADR-003 | [Why dbt for Transformations](docs/adr/003-why-dbt-for-transformations.md) | Accepted |
| ADR-004 | [Why Isolation Forest for Anomaly Detection](docs/adr/004-why-isolation-forest-for-anomaly-detection.md) | Accepted |
| ADR-005 | [Why Prophet over ARIMA](docs/adr/005-why-prophet-over-arima.md) | Accepted |
| ADR-006 | [S3 Cost Optimization Strategy](docs/adr/006-s3-cost-optimization-strategy.md) | Accepted |
| ADR-007 | [Typed Config with Dataclasses](docs/adr/007-typed-config-with-dataclasses.md) | Accepted |

---

## 📬 Contact
- GitHub: https://github.com/Divya-yaramala
- LinkedIn: linkedin.com/in/divya-yaramala (update with your actual LinkedIn URL)
- Email: divyayaramala145@gmail.com
- Open to: Full-time Data Engineer roles

---

## 📈 Progress Log

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

### ✅ Day 7 — End-to-End Pipeline Wiring
- Wired load_to_postgres_staging task in Airflow DAG with real implementation
- Created integration tests: full pipeline flow, S3 path consistency, idempotency
- Built scripts/run_pipeline_local.py with step timer and summary table
- Added local run command to Getting Started section
- 34/34 tests passing green

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

### ✅ Day 10 — CI/CD with GitHub Actions
- Created CI pipeline that runs all 40 tests on every push
- Created code quality checks: black, isort, flake8, mypy
- Fixed all formatting and linting issues across entire codebase
- Added CI and Code Quality badges to README
- Pipeline runs automatically on every commit

### ✅ Day 11 — Architecture Decision Records and Documentation
- Created 4 ADRs explaining key technology choices (Airflow, Snowflake, dbt, Isolation Forest)
- Created pipeline-overview.md covering data flow, components, data models, AI layer, and scheduling
- Created local-development.md with setup steps, test commands, common errors, and new ticker guide
- Created data-dictionary.md documenting all tables and columns across Postgres, Snowflake, and dbt
- Updated README with Documentation section and improved architecture diagram showing AI layer

### ✅ Day 12 — Dead Letter Queue Pattern
- Built dead letter queue module to capture failed pipeline records
- Failed records saved to S3 under errors/YYYY/MM/DD/step/
- DLQ replay function routes failed records back through correct pipeline step
- All 4 pipeline modules updated to send failures to DLQ
- DLQ replay wired as final Airflow task with TriggerRule.ALL_DONE
- 6 unit tests passing green

### ✅ Day 13 — Data Validation + Pipeline Monitoring
- Built data validation module with 7 checks per ticker
- Built pipeline monitoring module tracking run metrics per step
- Validation wired into DAG before staging load
- Monitoring report runs as final DAG task
- 10 unit tests passing green
- Full audit trail: validation reports + monitoring metrics saved to S3

### ✅ Day 14 — Slack Alerting + Health Checks
- Built Slack webhook alerting for pipeline success and failures
- Daily summary alert with success rate and slowest step
- Health check script verifying S3, Postgres, Snowflake, OpenAI connectivity
- Alerts wired into fetch and anomaly detection steps
- 10 unit tests passing green

### ✅ Day 15 — Data Lineage + Advanced dbt Models
- Built data lineage tracking module recording full data journey
- Lineage tracked: Yahoo Finance → S3 → anomalies → predictions → insights
- Added 3 advanced dbt mart models: daily summary, anomaly summary, prediction accuracy
- All 4 pipeline modules updated with lineage recording
- 6 unit tests passing green

### ✅ Day 16 — Incremental Loading + Backfill
- Built incremental loader detecting and filling data gaps automatically
- CLI backfill script with --ticker --start-date --end-date --dry-run flags
- Airflow DAG updated to use incremental loading by default
- Handles missing dates, deduplication, and partial loads gracefully
- 6 unit tests passing green — 78/78 total

### ✅ Day 17 — Data Quality Reporting + SLA Monitoring
- Built quality reporter scoring ticker validation results (0–100%) with SLA alerting at 80% threshold
- Built SLA monitor recording per-step durations and generating daily SLA compliance reports
- Slack alerts triggered automatically on quality SLA miss or step duration breach
- Airflow DAG wired with quality gate and SLA report tasks using TriggerRule.ALL_DONE
- 10 unit tests passing green — 88/88 total

### ✅ Day 18 — Cost Optimization + Resource Management
- Built S3 cost optimizer with storage analysis, old-data archiving, and monthly cost estimation
- Resource manager checks CPU/memory/disk thresholds before allowing the pipeline to run
- Pipeline skips automatically if any system resource is at a critical level
- Airflow DAG updated with resource gate and S3 optimization tasks
- 10 unit tests passing green — 98/98 total

### ✅ Day 19 — Configuration Management + Secrets Validation
- Built typed configuration manager using Python dataclasses for AWS, Postgres, Snowflake, OpenAI, and pipeline settings
- Centralized all env var loading with fail-fast validation on missing required vars
- CLI secrets validator checks all required vars before pipeline runs, with optional Slack warning
- Pipeline modules updated to use config manager instead of scattered os.getenv calls
- 10 unit tests passing green — 108/108 total

### ✅ Day 20 — World-Class README Polish
- Rewrote README with badges, features, architecture diagram
- Added complete project structure with module descriptions
- Added ADR summary table
- Professional presentation ready for senior engineers and recruiters

### ✅ Day 21 — Resume Bullets + Interview Prep
- Created 15 resume bullet points across Data Engineer and Analyst roles
- Documented answers to 10 common interview questions
- Added technical deep dives for Isolation Forest, Prophet, and testing strategy
- Ready to interview for Data Engineer roles

### ✅ Day 22 — LinkedIn Optimization + Job Search Strategy
- Created LinkedIn headline, about section, and featured project content
- Wrote 3 LinkedIn post templates for building in public
- Created job search tracker with target companies and weekly goals
- Kept repo clean — personal docs saved locally outside repo

### ✅ Day 23 — Final Code Review + Production Hardening
- Full code review across all 15 ingestion modules
- Added missing docstrings and type hints to all functions
- Added retry logic with tenacity for API calls (yfinance, OpenAI)
- All linters passing: black, isort, flake8, mypy
- 108/108 tests still passing green

### ✅ Day 24 — Loom Video Script + Portfolio Polish
- Created 3-minute Loom video script with screen recording checklist
- Created portfolio summary combining both projects
- Added Demo and Contact sections to README
- Portfolio ready to share with recruiters

### ✅ Day 25 — Final Portfolio Presentation
- Created project statistics document
- Updated README with final stats table
- Phase 4 Polish complete — portfolio ready!
- Starting Phase 5: Real-time streaming with Kafka (Project 2)

### ✅ Day 26 — REST API with FastAPI
- Built 7 REST endpoints exposing pipeline results
- Swagger UI auto-generated at /docs
- Endpoints for prices, anomalies, predictions, insights, summary
- 6 unit tests passing green
- API containerized with Docker

### ✅ Day 27 — Data Versioning + Pipeline Rollback
- Built data versioning module with MD5-based version IDs
- Snapshots saved to S3 under versions/YYYY/MM/DD/step/
- CLI rollback script with --dry-run preview mode
- Can rollback any pipeline step to any previous version
- 6 unit tests passing green

### ✅ Day 28 — ML Model Registry + Experiment Tracking
- Built ML model registry with versioning and promotion stages
- Models tracked: staging → production → archived lifecycle
- Experiment tracker logging params and metrics per run
- 10 unit tests passing green

### ✅ Day 29 — Automated Reports + Email Notifications
- Built HTML report generator combining quality, SLA, and monitoring metrics
- Email notifier with SMTP support for daily reports and alerts
- Wired into Airflow DAG as final tasks
- 10 unit tests passing green

---
*Built with ❤️ over 25 days as a portfolio project demonstrating production-grade data engineering.*
