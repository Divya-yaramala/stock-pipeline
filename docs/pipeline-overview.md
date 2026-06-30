# Pipeline Overview

This document describes the end-to-end architecture of the stock price data pipeline, including data flow, component responsibilities, data models, AI components, and scheduling.

## Table of Contents
- [Data Flow](#data-flow)
- [Component Responsibilities](#component-responsibilities)
- [Data Models](#data-models)
- [AI Components](#ai-components)
- [Scheduling](#scheduling)
- [Error Handling](#error-handling)

---

## 1. Data Flow

The pipeline moves data through five distinct layers, each with a clear responsibility:

1. **Ingestion (Yahoo Finance → S3):** Python fetches OHLCV (Open, High, Low, Close, Volume) data for five tickers — AAPL, MSFT, GOOGL, AMZN, TSLA — via the `yfinance` library. Each ticker's daily data is serialised to JSON and uploaded to S3 under `raw/stocks/YYYY/MM/DD/<TICKER>.json`.

2. **Staging (S3 → PostgreSQL):** The raw JSON files are read from S3 and inserted into PostgreSQL staging tables. An `ON CONFLICT DO NOTHING` clause ensures the operation is idempotent — re-running the pipeline for the same date never creates duplicate rows.

3. **Transformation (PostgreSQL → dbt models):** dbt reads from the staging schema and builds three model layers: `staging` views (light cleaning and type casting), `intermediate` models (daily metric calculations), and `mart` tables (analytics-ready aggregates). Data quality tests run automatically after each build.

4. **AI Layer (S3 → S3):** Three AI components run in parallel against the same raw S3 data:
   - **Anomaly Detection:** Isolation Forest flags unusual OHLCV movements and writes results to `processed/anomalies/YYYY/MM/DD/<TICKER>.json`.
   - **Price Prediction:** Facebook Prophet trains on 30 days of history and writes 5-day forecasts to `processed/predictions/YYYY/MM/DD/<TICKER>.json`.
   - **LLM Insights:** OpenAI GPT-3.5 reads prices, anomalies, and predictions to produce a 3-sentence market summary, saved to `processed/insights/YYYY/MM/DD/<TICKER>.json`.

5. **Warehousing (S3 → Snowflake):** All four processed data types are synced from S3 into Snowflake's `RAW` schema tables, making them available for BI tooling and ad-hoc SQL analysis.

---

## 2. Component Responsibilities

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| `ingestion/fetch_stocks.py` | Fetch OHLCV data and upload raw JSON to S3 | Python, yfinance, boto3 |
| `ingestion/anomaly_detector.py` | Detect unusual price/volume movements | scikit-learn Isolation Forest |
| `ingestion/price_predictor.py` | Forecast next 5 days of closing prices | Facebook Prophet |
| `ingestion/market_insights.py` | Generate natural language market summaries | OpenAI GPT-3.5 |
| `ingestion/snowflake_sync.py` | Sync all processed data from S3 to Snowflake | snowflake-connector-python |
| `scripts/setup_postgres.py` | Bootstrap staging schema and tables | psycopg2 |
| `scripts/setup_snowflake.py` | Bootstrap Snowflake database, schemas, warehouse, tables | snowflake-connector-python |
| `dbt_project/` | Transform and test staging data into analytics models | dbt Core |
| `airflow/dags/stock_pipeline_dag.py` | Orchestrate all tasks in dependency order | Apache Airflow 2.9 |

---

## 3. Data Models

### `staging.stock_prices_raw`
The raw ingest table. One row per ticker per trading day. Populated by `_load_to_postgres_staging` in the Airflow DAG.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Surrogate key |
| `ticker` | VARCHAR(10) | Stock symbol (e.g. AAPL) |
| `trade_date` | DATE | The trading date |
| `open_price` | NUMERIC(12,4) | Opening price |
| `high_price` | NUMERIC(12,4) | Intraday high |
| `low_price` | NUMERIC(12,4) | Intraday low |
| `close_price` | NUMERIC(12,4) | Closing price |
| `volume` | BIGINT | Shares traded |
| `ingested_at` | TIMESTAMP | Row insertion timestamp |

### `staging.stock_anomalies`
One row per ticker per trading day indicating whether an anomaly was detected.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Surrogate key |
| `ticker` | VARCHAR(10) | Stock symbol |
| `trade_date` | DATE | The trading date |
| `is_anomaly` | BOOLEAN | True if Isolation Forest flagged the day |
| `anomaly_score` | NUMERIC(10,6) | Raw isolation score (lower = more anomalous) |

### `staging.stock_predictions`
One row per ticker per forecasted date. Up to 5 rows per ticker per run.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Surrogate key |
| `ticker` | VARCHAR(10) | Stock symbol |
| `prediction_date` | DATE | The forecasted trading date |
| `predicted_close` | NUMERIC(12,4) | Prophet point forecast |
| `lower_bound` | NUMERIC(12,4) | 80% confidence interval lower bound |
| `upper_bound` | NUMERIC(12,4) | 80% confidence interval upper bound |

### `staging.stock_insights`
One row per ticker per day containing the GPT-generated market summary.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Surrogate key |
| `ticker` | VARCHAR(10) | Stock symbol |
| `insight_date` | DATE | The date the insight was generated |
| `insight_text` | TEXT | 3-sentence GPT market summary |

---

## 4. AI Components

### Anomaly Detection — Isolation Forest
- **Algorithm:** scikit-learn `IsolationForest` with `contamination=0.05` and `random_state=42`.
- **Features:** open, high, low, close, volume (5 dimensions).
- **Training window:** All available rows in today's JSON file (typically one row for the current day; more for historical backfills).
- **Output:** `is_anomaly` (boolean) and `anomaly_score` (float) per row.
- **Limitation:** No temporal context — each day is evaluated independently.

### Price Prediction — Facebook Prophet
- **Algorithm:** Facebook Prophet with `daily_seasonality=True`.
- **Training window:** Up to 30 days of historical closing prices loaded from S3.
- **Forecast horizon:** 5 trading days.
- **Output:** `ds` (date), `yhat` (forecast), `yhat_lower`, `yhat_upper` per future date.
- **Limitation:** Requires at least 2 data points; sparse history degrades accuracy.

### LLM Market Insights — OpenAI GPT-3.5
- **Model:** `gpt-3.5-turbo` with `max_tokens=200`, `temperature=0.7`.
- **Input context:** Today's OHLCV values, anomaly flag, and 5-day price forecast.
- **Output:** A 3-sentence professional market summary per ticker.
- **Limitation:** Quality depends on API availability and prompt engineering; no financial advice implied.

---

## 5. Scheduling

The pipeline is orchestrated by Apache Airflow and runs automatically on weekdays after US market close.

- **Schedule:** `0 18 * * 1-5` — 18:00 UTC, Monday through Friday.
- **Weekend guard:** A `ShortCircuitOperator` (`check_trading_day`) skips all downstream tasks on weekends, preventing unnecessary API calls and empty S3 writes.
- **Retry policy:** Each task retries up to 2 times with a 5-minute delay between attempts.
- **Max active runs:** 1 — prevents overlapping pipeline runs on the same day.

### Task Dependency Order

```
check_trading_day
    └── fetch_and_upload_to_s3
            └── load_to_postgres_staging
                    └── run_dbt_models
                            └── run_anomaly_detection
                                    └── run_price_prediction
                                            └── run_market_insights
                                                    └── run_snowflake_sync
```

---

## Error Handling

The pipeline uses a Dead Letter Queue (DLQ) pattern for fault tolerance.
Failed records are saved to S3 under errors/YYYY/MM/DD/step/ and can be
replayed without rerunning the full pipeline.

---

## Cost & Resource Management
- S3 storage optimizer archives raw data older than 30 days
- Monitoring data purged after 7 days to control costs
- Monthly cost estimated at $0.023/GB (S3 standard pricing)
- Resource manager checks CPU/memory/disk before pipeline runs
- Pipeline skips automatically if disk usage exceeds 90%

---

## Security
- No credentials stored in code — all secrets loaded from environment variables
- .env file gitignored — never committed to repository
- AWS credentials follow boto3 standard env/IAM chain
- Snowflake credentials loaded via dbt env_var() function
- validate_secrets.py checks all required vars before pipeline runs

---

## Performance Tips
- Run pipeline during off-peak hours (6 AM UTC) to avoid API rate limits
- Use incremental loading instead of full refresh whenever possible
- Archive S3 raw data older than 30 days to reduce storage costs
- Monitor step durations using SLA monitor to identify bottlenecks
- Use Snowflake warehouse auto-suspend to reduce compute costs

## Technical Indicators

The pipeline calculates 4 technical indicators daily for each ticker:

| Indicator | Formula | Signal |
|---|---|---|
| SMA (20) | Average of last 20 closes | Trend direction |
| RSI (14) | Wilder smoothed RS method | >70 overbought, <30 oversold |
| Bollinger Bands | SMA ± 2 standard deviations | Volatility and breakouts |
| MACD | EMA(12) - EMA(26) | Momentum and trend changes |

## Financial Analytics Layer

The pipeline includes advanced financial analytics:

| Module | Capability | Output |
|---|---|---|
| technical_indicators.py | SMA, RSI, Bollinger Bands, MACD | Daily signals per ticker |
| news_sentiment.py | Keyword-based news scoring | BULLISH/BEARISH/NEUTRAL |
| market_correlation.py | Pearson correlation matrix | Correlation pairs + Beta |
| portfolio_tracker.py | Daily portfolio value | Value, weights, returns |

## Alerting Rules Engine
The pipeline evaluates 5 default rules daily:

| Rule | Metric | Threshold | Severity |
|---|---|---|---|
| R001 | Anomaly rate | > 20% | HIGH |
| R002 | Quality score | < 80% | HIGH |
| R003 | SLA met rate | < 90% | MEDIUM |
| R004 | Error rate | > 5% | HIGH |
| R005 | Prediction accuracy | < 70% | MEDIUM |

Custom rules can be added via S3: monitoring/rules/custom_rules.json

## API Quick Reference
| API | Port | URL |
|---|---|---|
| REST | 8000 | http://localhost:8000/docs |
| GraphQL | 8001 | http://localhost:8001/graphql |
| WebSocket | 8002 | ws://localhost:8002/ws/prices |

## MLOps Quick Reference
| Stage | Module |
|---|---|
| Train | model_comparator.py, ensemble_model.py |
| Register | model_registry.py |
| Track | experiment_tracker.py |
| Serve | model_server.py |
| Monitor | drift_detector.py |
| Retrain | retraining_trigger.py |
