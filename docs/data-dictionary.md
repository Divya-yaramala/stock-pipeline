# Data Dictionary

This document describes every table and column in the stock pipeline, covering the PostgreSQL staging layer and all dbt models. Column types shown are the PostgreSQL / Snowflake types used at each layer.

## Data Freshness
| Table | Update Frequency | Source |
|---|---|---|
| staging.stock_prices_raw | Daily 6 AM UTC | Yahoo Finance API |
| staging.stock_anomalies | Daily after ingestion | Isolation Forest model |
| staging.stock_predictions | Daily after ingestion | Prophet model |
| staging.stock_insights | Daily after ingestion | GPT-3.5 API |
| Snowflake marts | Daily after dbt run | dbt transformations |

---

## Table of Contents
- [Postgres Staging Tables](#postgres-staging-tables)
- [Snowflake RAW Tables](#snowflake-raw-tables)
- [dbt Models](#dbt-models)

---

## PostgreSQL Staging Tables

These tables are populated by the Airflow DAG and serve as the source for dbt transformations.

---

### `staging.stock_prices_raw`

Raw OHLCV data ingested from S3. One row per ticker per trading day.

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | SERIAL | No | Auto-incrementing surrogate key | `1` |
| `ticker` | VARCHAR(10) | No | Stock ticker symbol | `AAPL` |
| `trade_date` | DATE | No | The trading date | `2026-05-19` |
| `open_price` | NUMERIC(12,4) | Yes | Price at market open | `189.5000` |
| `high_price` | NUMERIC(12,4) | Yes | Intraday highest price | `192.3400` |
| `low_price` | NUMERIC(12,4) | Yes | Intraday lowest price | `187.8200` |
| `close_price` | NUMERIC(12,4) | No | Price at market close | `191.0500` |
| `volume` | BIGINT | Yes | Number of shares traded | `55432100` |
| `ingested_at` | TIMESTAMP | No | UTC timestamp when row was inserted | `2026-05-19 18:05:32` |

**Constraints:** `UNIQUE (ticker, trade_date)` — prevents duplicate rows for the same ticker and date.

---

### `staging.stock_anomalies`

Anomaly detection results produced by the Isolation Forest model. One row per ticker per trading day.

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | SERIAL | No | Auto-incrementing surrogate key | `1` |
| `ticker` | VARCHAR(10) | No | Stock ticker symbol | `TSLA` |
| `trade_date` | DATE | No | The trading date the model was applied to | `2026-05-19` |
| `is_anomaly` | BOOLEAN | No | `true` if the day was flagged as anomalous | `false` |
| `anomaly_score` | NUMERIC(10,6) | Yes | Raw Isolation Forest decision score (lower = more anomalous) | `-0.052341` |

**Constraints:** `UNIQUE (ticker, trade_date)`.

**Notes:** The `contamination` parameter is set to `0.05`, meaning roughly 5% of rows are expected to be flagged as anomalies in a typical dataset.

---

### `staging.stock_predictions`

Price forecasts produced by Facebook Prophet. Up to 5 rows per ticker per pipeline run (one per forecasted day).

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | SERIAL | No | Auto-incrementing surrogate key | `1` |
| `ticker` | VARCHAR(10) | No | Stock ticker symbol | `MSFT` |
| `prediction_date` | DATE | No | The future date being forecast | `2026-05-20` |
| `predicted_close` | NUMERIC(12,4) | Yes | Prophet point estimate for closing price | `415.2300` |
| `lower_bound` | NUMERIC(12,4) | Yes | Lower bound of 80% confidence interval | `409.1100` |
| `upper_bound` | NUMERIC(12,4) | Yes | Upper bound of 80% confidence interval | `421.5600` |

**Constraints:** `UNIQUE (ticker, prediction_date)`.

---

### `staging.stock_insights`

GPT-generated natural language market summaries. One row per ticker per pipeline run.

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | SERIAL | No | Auto-incrementing surrogate key | `1` |
| `ticker` | VARCHAR(10) | No | Stock ticker symbol | `GOOGL` |
| `insight_date` | DATE | No | The date the insight was generated | `2026-05-19` |
| `insight_text` | TEXT | Yes | 3-sentence GPT-3.5 market summary | `"Alphabet closed up 1.2%..."` |

**Constraints:** `UNIQUE (ticker, insight_date)`.

---

## Snowflake Raw Tables

Mirrors of the PostgreSQL staging tables, synced from S3 by `ingestion/snowflake_sync.py`. Stored in `STOCK_PIPELINE_DB.RAW`.

---

### `RAW.STOCK_PRICES`

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `ID` | NUMBER AUTOINCREMENT | No | Surrogate key | `1` |
| `TICKER` | VARCHAR(10) | No | Stock ticker symbol | `AAPL` |
| `TRADE_DATE` | DATE | No | Trading date | `2026-05-19` |
| `OPEN_PRICE` | NUMBER(12,4) | Yes | Opening price | `189.5000` |
| `HIGH_PRICE` | NUMBER(12,4) | Yes | Intraday high | `192.3400` |
| `LOW_PRICE` | NUMBER(12,4) | Yes | Intraday low | `187.8200` |
| `CLOSE_PRICE` | NUMBER(12,4) | No | Closing price | `191.0500` |
| `VOLUME` | NUMBER(20) | Yes | Shares traded | `55432100` |
| `INGESTED_AT` | TIMESTAMP_NTZ | No | Insertion timestamp | `2026-05-19 18:05:32` |

**Clustering key:** `(TICKER, TRADE_DATE)` — optimises partition pruning for ticker- and date-filtered queries.

---

### `RAW.STOCK_ANOMALIES`

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `ID` | NUMBER AUTOINCREMENT | No | Surrogate key | `1` |
| `TICKER` | VARCHAR(10) | No | Stock ticker symbol | `TSLA` |
| `TRADE_DATE` | DATE | No | Trading date | `2026-05-19` |
| `IS_ANOMALY` | BOOLEAN | No | Anomaly flag | `FALSE` |
| `ANOMALY_SCORE` | NUMBER(10,6) | Yes | Isolation Forest score | `-0.052341` |

---

### `RAW.STOCK_PREDICTIONS`

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `ID` | NUMBER AUTOINCREMENT | No | Surrogate key | `1` |
| `TICKER` | VARCHAR(10) | No | Stock ticker symbol | `MSFT` |
| `PREDICTION_DATE` | DATE | No | Forecasted date | `2026-05-20` |
| `PREDICTED_CLOSE` | NUMBER(12,4) | Yes | Point forecast | `415.2300` |
| `LOWER_BOUND` | NUMBER(12,4) | Yes | Confidence interval lower | `409.1100` |
| `UPPER_BOUND` | NUMBER(12,4) | Yes | Confidence interval upper | `421.5600` |

---

### `RAW.STOCK_INSIGHTS`

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `ID` | NUMBER AUTOINCREMENT | No | Surrogate key | `1` |
| `TICKER` | VARCHAR(10) | No | Stock ticker symbol | `GOOGL` |
| `INSIGHT_DATE` | DATE | No | Insight generation date | `2026-05-19` |
| `INSIGHT_TEXT` | TEXT | Yes | GPT market summary | `"Alphabet closed up..."` |

---

## dbt Models

dbt models are defined in `dbt_project/models/`. Staging models are materialised as views; mart models as tables.

---

### `staging.stg_stock_prices` (view)

A lightly cleaned view over `staging.stock_prices_raw`. Renames columns and casts types to the project's standard naming convention.

| Column | Type | Description | Source Column |
|--------|------|-------------|---------------|
| `ticker` | VARCHAR | Stock ticker symbol | `ticker` |
| `trade_date` | DATE | Trading date | `trade_date` |
| `open_price` | NUMERIC | Opening price | `open_price` |
| `high_price` | NUMERIC | Intraday high | `high_price` |
| `low_price` | NUMERIC | Intraday low | `low_price` |
| `close_price` | NUMERIC | Closing price | `close_price` |
| `volume` | BIGINT | Shares traded | `volume` |

**Tests:** `not_null` on `ticker`, `trade_date`, `close_price`; `unique` on `(ticker, trade_date)`.

---

### `marts.fct_stock_prices` (table)

Fact table joining prices with daily return calculations. Analytics-ready for BI tools.

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | VARCHAR | Stock ticker symbol |
| `trade_date` | DATE | Trading date |
| `open_price` | NUMERIC | Opening price |
| `high_price` | NUMERIC | Intraday high |
| `low_price` | NUMERIC | Intraday low |
| `close_price` | NUMERIC | Closing price |
| `volume` | BIGINT | Shares traded |
| `daily_range` | NUMERIC | `high_price - low_price` |
| `daily_return_pct` | NUMERIC | Day-over-day close price change % |

---

### `marts.dim_tickers` (table)

Dimension table of tracked stock tickers. Sourced from the `stock_symbols` dbt seed.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `symbol` | VARCHAR | Ticker symbol | `AAPL` |
| `name` | VARCHAR | Company full name | `Apple Inc.` |
| `sector` | VARCHAR | GICS sector | `Technology` |
