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

## S3 Cost Management
The pipeline manages S3 costs through:

### Retention Policies (10 prefixes)
| Prefix | Retention |
|---|---|
| raw/stocks/ | 90 days |
| processed/anomalies/ | 180 days |
| processed/predictions/ | 90 days |
| processed/insights/ | 90 days |
| processed/sentiment/ | 30 days |
| processed/technical/ | 30 days |
| processed/features/ | 30 days |
| cache/ | 7 days |
| chaos/ | 30 days |
| testing/ | 30 days |

### Storage Classes
- Active data (< 30 days): S3 Standard
- Older data (30-90 days): S3 Standard-IA
- Archive (90+ days): S3 Glacier

### Monthly Cost Estimate
- 100GB active data: ~$2.30/month
- 500GB Glacier archive: ~$2.00/month
- Total pipeline storage: ~$5/month

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

---

## Data Lineage Map
```
Yahoo Finance API
      ↓
raw_prices (S3 + PostgreSQL)
      ↓
validated_prices (data_validator)
      ↓
├── postgres_staging (PostgreSQL)
│       ↓
│   snowflake_raw (Snowflake sync)
│       ↓
│   snowflake_marts (dbt transformations)
│
├── anomaly_results (Isolation Forest ML)
├── price_predictions (Prophet forecasting)
├── ensemble_predictions (RF + GB + Linear)
├── sentiment_scores (keyword NLP)
├── technical_indicators (SMA, RSI, BB, MACD)
├── market_correlation (Pearson matrix)
└── feature_store (S3 feature cache)
      ↓
REST API + GraphQL API + WebSocket API
```
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

## Alerting Architecture
The pipeline uses a dual notification system:

### Real-Time Alerts (Slack)
anomaly_detector.py → slack_alerter.alert_anomaly_detected()
quality_reporter.py → slack_alerter.alert_quality_warning()
pipeline failures → slack_alerter.alert_pipeline_failure()
end of day → slack_alerter.send_daily_summary()

### Daily Reports (Email)
report_generator.py → email_notifier.send_daily_report_email()
HTML report saved to S3: reports/daily/YYYY/MM/DD/

### Alert Severity Levels
| Severity | Color | Trigger |
|---|---|---|
| CRITICAL | 🔴 Red | Anomaly, pipeline failure |
| WARNING | 🟡 Yellow | Quality < 80%, SLA breach |
| INFO | 🟢 Green | Predictions ready, daily summary |

## 📊 Dashboard Layer
The pipeline includes a Streamlit dashboard for visual exploration:

| Page | URL | Description |
|---|---|---|
| Main | http://localhost:8503 | Price charts, anomalies, predictions |
| Portfolio | http://localhost:8503/portfolio | Holdings tracker |
| Anomalies | http://localhost:8503/anomalies | Real-time anomaly monitor |
| Predictions | http://localhost:8503/predictions | 5-day Prophet forecasts |

Start: streamlit run dashboard/app.py --server.port 8503

## Quality Gate Layer
Every pipeline run passes through 5 quality gates:

**Stage 1 — After Ingestion:**
| Gate | Check | Action |
|---|---|---|
| G001 freshness_gate | Must be < 25 hours old | BLOCK if fails |
| G002 completeness_gate | Must be > 80% complete | BLOCK if fails |

**Stage 2 — After ML:**
| Gate | Check | Action |
|---|---|---|
| G003 quality_score_gate | Must be > 75% | WARN if fails |
| G004 anomaly_rate_gate | Must be < 30% anomalies | WARN if fails |
| G005 prediction_accuracy_gate | Must be > 60% accurate | BLOCK if fails |

**Gate Results:**
- ✅ PASS → Pipeline continues to next stage
- ⚠️ WARN → Pipeline continues + Slack warning sent
- ❌ BLOCK → Pipeline stops + Auto remediation triggered

## Monitoring Architecture

### Layer 1: Real-Time Monitoring (every 5-15 minutes)
`realtime_monitor.py` runs continuously checking:
- Yahoo Finance API availability
- S3 data freshness per ticker
- Pipeline processing lag
- DLQ error rate
- System resource usage

### Layer 2: SLA Monitoring (daily)
`sla_reporter.py` tracks 6 daily SLA targets:
- All stages must complete by specific hours
- 30-day compliance trend reported weekly

### Layer 3: Observability (daily)
`data_observatory.py` checks per ticker:
- Data freshness (< 25 hours)
- Data completeness (> 80%)
- Price anomaly rate (< 5%)

### Alerting Flow
```
Issue detected → Slack alert → Auto remediation triggered
                             → Quality gate blocks downstream
                             → Health dashboard updated
```

## Feature Flag Layer
10 feature flags control pipeline behavior:

### Always-On Features (default True)
- enable_gpt_insights — GPT market summaries per ticker
- enable_ensemble_models — RF + GB + Linear ensemble
- enable_news_sentiment — Keyword-based sentiment analysis
- enable_slack_alerts — Real-time Slack notifications
- enable_email_reports — Daily HTML email reports
- enable_snowflake_sync — Snowflake warehouse sync
- enable_auto_remediation — Automatic issue remediation

### Opt-In Features (default False)
- enable_kafka_streaming — Real-time Kafka producer/consumer
- enable_chaos_engineering — Chaos failure injection
- enable_ab_testing — ML model A/B experiments

### Toggling Flags
```bash
python -c "from ingestion.feature_flag_manager import enable_flag; import os; enable_flag('enable_kafka_streaming', os.getenv('AWS_BUCKET_NAME'))"
```

## Data Mesh Architecture

### Domain: market_data
Owner: data_engineering
Products: stock_prices (DP001)
S3 paths: raw/stocks/, processed/

### Domain: ml_insights
Owner: ml_team
Products: anomaly_signals (DP002), price_forecasts (DP003)
S3 paths: processed/anomalies/, processed/predictions/

### Domain: nlp_insights
Owner: data_engineering
Products: market_sentiment (DP004)
S3 paths: processed/sentiment/, processed/insights/

### Domain: analytics
Owner: analytics_team
Products: portfolio_analytics (DP005)
S3 paths: portfolio/, reports/bi/

### Event Flow
```
data_ingested → anomaly_detected → prediction_generated
      ↓               ↓                    ↓
quality_gate   sla_met/missed      model_retrain_triggered
      ↓
pipeline_completed / pipeline_failed
```

## Data Contracts and Schema Registry

### Data Contract Flow
```
Producer (fetch_stocks.py) → validate_against_contract()
      ↓
Contract C001: stock_price_event v1.0.0
      ↓
Violations logged → Slack alert if violations > 0
      ↓
Consumer (anomaly_detector.py, model_comparator.py)
```

### Schema Registry
4 schemas registered at pipeline startup:
- stock_prices_raw v1.0.0
- stock_anomalies v1.0.0
- stock_predictions v1.0.0
- stock_sentiment v1.0.0

Schema evolution validated before any schema change:
```
Old schema → check_contract_compatibility() → New schema
If breaking: ValueError raised, migration required
```

## Data Privacy Layer

### PII Detection Flow
Every file written to S3 can be scanned:
```
raw/stocks/ → pii_detector.scan_s3_file_for_pii()
audit/ → pii_detector.run_pii_scan()

PII found → mask_pii() → save masked version
          → Slack alert → security/pii_scan/ report
```

### Privacy Policy Enforcement
| S3 Prefix | Policy | Classification |
|---|---|---|
| raw/stocks/ | financial_data | CONFIDENTIAL |
| processed/ | ml_features | INTERNAL |
| audit/ | audit_logs | CONFIDENTIAL |
| cache/ | cache_data | PUBLIC |

### Data Classification Flow
```
New dataset → check_policy_compliance()
            → PASS: proceed normally
            → FAIL: log violation + Slack alert
```

---

## Storage Architecture

### Active Data (HOT — S3 Standard)
Data written by pipeline daily:
```
raw/stocks/YYYY/MM/DD/    → STANDARD for 90 days
processed/*               → STANDARD for 30-90 days
```

### Archived Data (COLD — S3 Glacier)
Automatically moved after retention period:
```
raw/stocks/               → GLACIER after 90 days
processed/anomalies/      → GLACIER after 180 days
```

### Permanent Data (never archived)
```
audit/            → indefinite retention
lineage/          → indefinite retention
models/registry/  → indefinite retention
```

### Storage Cost Flow
```
Day 1-30:   All data in HOT  ($0.023/GB)
Day 30-90:  Old data moves to WARM ($0.0125/GB)
Day 90-365: Old data moves to COLD ($0.004/GB)
Day 365+:   Data deleted (saves 100%)
```

---

## API Layer (v2.0.0)

### REST API (Port 8000) — 13 endpoints
Categories:
- system: health check, feature flags
- market_data: prices, summary
- ml: anomalies, predictions
- ai: GPT insights
- nlp: news sentiment
- quality: quality gates
- governance: data products
- observability: events, pipeline health
- security: PII scan

Start: `uvicorn api.main:app --reload --port 8000`
Docs: http://localhost:8000/docs

### GraphQL API (Port 8001) — 4 resolvers
Resolvers: tickers, stockPrices, anomalies, portfolioSummary
Playground: http://localhost:8001/graphql

### WebSocket API (Port 8002) — 2 streams
Streams: /ws/prices (30s), /ws/alerts (60s)
Status: http://localhost:8002/ws/status

### API Selection Guide
- REST: One-time queries, simple integrations
- GraphQL: Complex queries, flexible field selection
- WebSocket: Real-time streaming, live dashboards

---

## Testing Architecture

### Unit Tests (tests/)
465 tests covering all 75 ingestion modules
```bash
pytest tests/ -v
```

### Integration Tests (tests/integration/)
5 tests covering pipeline flows:
- fetch → validate flow
- validate → anomaly flow
- sentiment → S3 flow
- cache integration
- portfolio → snapshot flow

### E2E Tests (tests/e2e/)
6 tests covering all 3 APIs:
- REST API: /health, /prices, /anomalies, /summary
- GraphQL API: /health
- WebSocket API: /ws/status

### Performance Benchmarks
- S3 operations: put, get, list
- Data processing: validation, feature engineering
- Regression threshold: 20% slower than baseline

### Coverage Targets
- Overall: > 85%
- Core ingestion modules: > 90%
- API layer: > 85%

## Streaming Analytics Layer

### Real-Time Processing (streaming_analytics.py)
Sliding window (size=20) processes each new price:
```
price → update_window() → calculate_window_stats()
                        → detect_streaming_anomaly()
                        → calculate_streaming_rsi()
```

Z-score > 2.5 → SPIKE alert
Z-score < -2.5 → DROP alert

### Real-Time Aggregation (realtime_aggregator.py)
OHLCV bars (5-minute windows):
```
prices → aggregate_ohlcv() → OHLCV bars
       → calculate_vwap() → fair value
       → calculate_volume_profile() → POC
       → detect_momentum() → bullish/bearish/neutral
```

### Integration with Kafka Layer
```
Kafka consumer → streaming_analytics.process_price_stream()
              → realtime_aggregator.run_realtime_aggregation()
              → S3 streaming/analytics/
```

## Distributed Processing Architecture

### Parallel Ticker Processing
5 tickers processed simultaneously:

```
ThreadPoolExecutor(max_workers=5)
├── Worker 1: AAPL → fetch → validate → anomaly → predict
├── Worker 2: MSFT → fetch → validate → anomaly → predict
├── Worker 3: GOOGL → fetch → validate → anomaly → predict
├── Worker 4: AMZN → fetch → validate → anomaly → predict
└── Worker 5: TSLA → fetch → validate → anomaly → predict
```

Result: 5x speedup vs sequential processing

### Parallel S3 Uploads
10 workers for batch uploads:
```
ThreadPoolExecutor(max_workers=10)
├── Workers 1-10: parallel put_object calls
```
Result: 80%+ reduction in upload time

### Pipeline Profiling
After each run:
```
run_pipeline_profiling() → step timings → bottleneck detection
                        → recommendations → S3 report
```

## NLP and Text Analytics Layer

### NLP Pipeline (nlp_processor.py)
Input: News headlines and articles per ticker
Processing:
1. tokenize_text() — remove stopwords, lowercase
2. extract_financial_entities() — tickers, amounts, percentages
3. calculate_text_sentiment() — 15 financial domain terms
4. summarize_text() — top 3 sentences by term density
5. analyze_earnings_report() — full report analysis

Output: S3 processed/nlp/YYYY/MM/DD/ticker.json

### Text Analytics (text_analytics.py)
Input: News corpus (list of articles)
Processing:
1. calculate_tfidf() — keyword importance across corpus
2. find_key_phrases() — noun phrase extraction
3. classify_news_category() — 6 category classification
4. extract_price_targets() — analyst price target extraction

Output: S3 processed/text_analytics/YYYY/MM/DD/ticker.json

### Integration with Sentiment Module
nlp_processor.py → richer analysis than news_sentiment.py
news_sentiment.py → simpler keyword counting (faster)
Use news_sentiment.py for daily pipeline
Use nlp_processor.py for deep analysis


## Enhanced Forecasting Architecture

### Model 1: Prophet (60% weight)
Input: 90 days of daily close prices
Output: 5-day forecast with 80% confidence intervals
Strengths: trend + seasonality + holiday effects

### Model 2: Ensemble (40% weight)
Input: Feature matrix (SMA, RSI, BB, MACD, volume, momentum)
Models: RF + Gradient Boosting + Linear Regression
Output: 5-day point predictions

### Blending Layer
blended = Prophet × 0.6 + Ensemble × 0.4
Reduces individual model variance

### Scenario Layer
bull = blended + 2 × 20-day volatility
base = blended
bear = blended - 2 × 20-day volatility

### Confidence Intervals
Lower = prediction - (volatility × z_score)
Upper = prediction + (volatility × z_score)
z_score = 1.96 for 95% confidence

### Time Series Analysis (pre-forecast)
detect_trend() → uptrend/downtrend/sideways
detect_seasonality() → seasonal=True/False
calculate_volatility_regime() → low/medium/high
