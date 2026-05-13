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

# 3. Open Airflow UI at http://localhost:8080  (admin / admin)
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
