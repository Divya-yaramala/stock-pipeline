# Resume Bullet Points — AI-Powered Stock Price Pipeline

## For Data Engineer Roles

### Core Pipeline
- Built end-to-end AI-powered stock price pipeline processing 5 tickers daily using Python, Apache Airflow, dbt, PostgreSQL, and Snowflake — fully automated with 13-task DAG
- Designed and implemented raw data lake on AWS S3 with date partitioning (raw/stocks/YYYY/MM/DD/) supporting incremental loads and 6-month historical backfill
- Built idempotent data ingestion using ON CONFLICT DO NOTHING pattern ensuring zero duplicate records across 108 unit and integration tests
- Implemented dead letter queue pattern capturing failed pipeline records to S3 for automatic replay — ensuring zero data loss on failures

### AI/ML Components
- Integrated scikit-learn Isolation Forest anomaly detection model identifying unusual stock price movements across 5 OHLCV features daily
- Built Facebook Prophet time series forecasting model predicting next 5 days closing prices with lower/upper confidence bounds per ticker
- Implemented OpenAI GPT-3.5 market insight generator producing 3-sentence professional summaries per ticker using live anomaly and prediction data

### Data Quality & Monitoring
- Implemented 7-point data validation framework (row count, nulls, price ranges, OHLCV integrity) with 80% SLA threshold and automatic Slack alerting
- Built pipeline monitoring system tracking per-step execution metrics, success rates, and SLA compliance — generating daily S3 reports
- Created data lineage tracker recording full audit trail from Yahoo Finance API through Snowflake marts for every pipeline run

### Infrastructure & DevOps
- Set up CI/CD pipeline using GitHub Actions running 108 tests, black, isort, flake8, and mypy on every push — maintaining 100% pass rate
- Containerized pipeline with Docker Compose running Airflow 2.9, PostgreSQL, and supporting services for reproducible local development
- Built S3 cost optimizer archiving raw data older than 30 days and estimating monthly storage costs at $0.023/GB

### dbt & Transformations
- Built 6 dbt models across staging and marts layers including fct_stock_prices, fct_anomaly_summary, fct_prediction_accuracy, and dim_tickers
- Documented 7 Architecture Decision Records (ADRs) explaining technology choices including Airflow vs Prefect, Snowflake vs Redshift, dbt vs custom SQL

## For Data Analyst Roles
- Designed analytics-ready mart tables in Snowflake combining stock prices, ML anomaly scores, price predictions, and LLM insights in single queryable fact table
- Built dbt prediction accuracy model using LAG() window function to compare predicted vs actual closing prices with direction_correct flag
- Created data dictionary documenting every column across 4 staging tables, 4 Snowflake RAW tables, and 6 dbt models

## One-Line Resume Summary
Built an AI-powered stock price pipeline using Python, Airflow, dbt, Snowflake, and AWS — featuring ML anomaly detection, Prophet forecasting, GPT insights, CI/CD, and 108 automated tests.

## Talking Points for Recruiters (Non-Technical)

- "I built a fully automated system that runs every day without human intervention"
- "The pipeline has 108 automated tests that run on every code change"
- "I used the same tools that Netflix, Airbnb, and Uber use for their data pipelines"
- "The AI components detect unusual market behavior and predict future prices automatically"
- "I documented every technology decision so the next engineer knows exactly why things were built this way"

## Skills Demonstrated (for salary negotiation)

| Skill | Market Value | Evidence |
|---|---|---|
| Apache Airflow | Senior DE skill | 13-task production DAG |
| dbt Core | In-demand skill | 6 models with tests |
| Snowflake | Premium skill | Full warehouse setup |
| AWS S3 | Cloud skill | Raw data lake pattern |
| CI/CD | DevOps skill | GitHub Actions workflows |
| ML Integration | AI skill | 3 AI components |
| pytest | Quality skill | 108 tests |
