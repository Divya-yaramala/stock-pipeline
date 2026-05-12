# Stock Price Data Pipeline

A production-style data engineering portfolio project demonstrating an end-to-end stock price pipeline using Python, Apache Airflow, dbt, Snowflake, and AWS S3.

---

## Architecture

```
                        ┌─────────────────────────────────────────────────────┐
                        │                  Apache Airflow (Orchestration)      │
                        │                                                       │
                        │   [fetch_stock_prices] → [upload_to_s3] →            │
                        │   [load_to_snowflake]  → [run_dbt_models]            │
                        └─────────────────────────────────────────────────────┘
                                │              │              │
                                ▼              ▼              ▼
                     ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
                     │  Yahoo Finance│  │   AWS S3     │  │    Snowflake     │
                     │  (Raw Data)  │  │  (Raw Layer) │  │  (Warehouse)     │
                     └──────────────┘  └──────────────┘  └──────────────────┘
                                                                   │
                                                                   ▼
                                                        ┌──────────────────┐
                                                        │       dbt        │
                                                        │  staging → marts │
                                                        └──────────────────┘
```

**Data Flow:**
1. **Ingestion** — Python fetches daily OHLCV stock data from Yahoo Finance API
2. **Raw Storage** — Raw JSON/CSV files land in AWS S3 (raw layer)
3. **Loading** — Snowflake `COPY INTO` loads raw files from S3 into a staging table
4. **Transformation** — dbt models clean, deduplicate, and aggregate data into analytics-ready marts
5. **Orchestration** — Airflow DAG runs the full pipeline on a daily schedule

---

## Tech Stack

| Layer           | Tool / Service       |
|-----------------|----------------------|
| Orchestration   | Apache Airflow 2.x   |
| Ingestion       | Python, yfinance     |
| Raw Storage     | AWS S3               |
| Data Warehouse  | Snowflake            |
| Transformation  | dbt (Snowflake adapter) |
| Infrastructure  | boto3 (AWS SDK)      |
| Testing         | pytest               |

---

## Project Structure

```
portfolio/
├── dags/
│   └── stock_price_pipeline.py     # Airflow DAG definition
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── staging/
│       │   └── stg_stock_prices.sql    # Clean raw data
│       └── marts/
│           └── stock_price_daily_summary.sql  # Analytics-ready aggregate
├── ingestion/
│   └── fetch_stock_prices.py       # Pull data from Yahoo Finance
├── infrastructure/
│   └── s3_setup.py                 # S3 bucket and prefix management
├── config/
│   └── config.yaml                 # Pipeline configuration
├── tests/
│   └── test_ingestion.py           # Unit tests for ingestion layer
└── requirements.txt
```

---

## Setup

### Prerequisites

- Python 3.10+
- AWS account with S3 access
- Snowflake account
- Apache Airflow 2.x

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment

Copy and fill in your credentials:

```bash
cp config/config.yaml.example config/config.yaml
```

Set environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export SNOWFLAKE_ACCOUNT=your_account
export SNOWFLAKE_USER=your_user
export SNOWFLAKE_PASSWORD=your_password
```

### Initialize dbt

```bash
cd dbt
dbt deps
dbt debug
```

### Run the pipeline manually

```bash
# Fetch and upload to S3
python ingestion/fetch_stock_prices.py

# Run dbt transformations
cd dbt && dbt run
```

### Trigger Airflow DAG

Place `dags/stock_price_pipeline.py` in your Airflow `dags/` folder and trigger via UI or CLI:

```bash
airflow dags trigger stock_price_pipeline
```

---

## dbt Models

### `staging.stg_stock_prices`
Casts and cleans raw Snowflake-loaded data: deduplicate, type-cast dates, rename columns.

### `marts.stock_price_daily_summary`
Aggregates per ticker per day: open, close, high, low, volume, daily return %.

---

## Tests

```bash
pytest tests/
```

---

## Author

**Divya Yaramala** — Data Engineer
- GitHub: [Divya-yaramala](https://github.com/Divya-yaramala)
- Email: divyayaramala145@gmail.com
