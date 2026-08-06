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

## Market Analytics Layer

### Graph Analysis (market_graph_analyzer.py)
Daily run after correlation matrix calculated:
```
correlation_matrix → build_correlation_graph(threshold=0.7)
                  → calculate_node_centrality()
                  → find_market_clusters()
                  → detect_market_leader()
                  → calculate_market_stability()
Output: S3 processed/graph_analysis/YYYY/MM/DD/analysis.json
```

### Sector Analysis (sector_analyzer.py)
Daily run after ticker returns calculated:
```
ticker_returns → calculate_sector_returns()
              → identify_sector_leaders()
              → calculate_sector_rotation()
              → compare_to_benchmark()
Output: S3 processed/sector_analysis/YYYY/MM/DD/analysis.json
```

### Correlation → Graph → Sector Pipeline
```
raw_prices → correlation_matrix (market_correlation.py)
          → graph_analysis (market_graph_analyzer.py)
          → sector_analysis (sector_analyzer.py)
          → portfolio_insights (portfolio_tracker.py)
```

## Risk Analytics Layer

### Individual Ticker Risk (risk_analyzer.py)
For each ticker daily:
```
daily_returns → calculate_var(confidence=0.95)
              → calculate_cvar(confidence=0.95)
              → calculate_risk_metrics()
              → classify_risk_level()
Output: S3 processed/risk_analysis/YYYY/MM/DD/analysis.json
```

### Portfolio Risk
```
portfolio_weights + ticker_returns
→ calculate_portfolio_var()
→ combined portfolio VaR and CVaR
```

### Portfolio Optimization (portfolio_optimizer.py)
```
ticker_returns → calculate_efficient_frontier_points(n=100)
              → find_max_sharpe_portfolio()
              → find_min_volatility_portfolio()
              → calculate_rebalancing_trades()
Output: S3 processed/portfolio_optimization/YYYY/MM/DD/result.json
```

### Risk → Portfolio → Rebalancing Flow
```
risk_analysis → identify high-risk tickers
             → portfolio_optimization → optimal weights
             → rebalancing_trades → actionable trades
```

## Event-Driven Workflow Layer

### Trigger Definitions (event_workflow.py)
5 triggers covering critical pipeline events:
```
T001: anomaly_detected      → HIGH     → 3 actions
T002: quality_gate_blocked  → CRITICAL → 3 actions
T003: model_drift_detected  → MEDIUM   → 3 actions
T004: sla_missed            → HIGH     → 3 actions
T005: pipeline_completed    → LOW      → 3 actions
```

### Notification Channels (notification_manager.py)
3 channels with severity routing:
```
LOW:      S3 log only
MEDIUM:   S3 log + Slack
HIGH:     S3 log + Slack + escalation
CRITICAL: ALL channels (Slack + email + S3 + pause)
```

### Integration with Event Bus
```
event_bus.publish_event() → event_workflow.process_event()
                         → notification_manager.send_notification()
                         → save_workflow_log()
```

### Workflow History
All processed events saved to:
```
S3: workflows/logs/YYYY/MM/DD/event_type_timestamp.json
```
Enables daily audit of all triggered workflows

## Self-Service Analytics Layer

### Available Metrics (self_service_analytics.py)
8 metrics across 5 categories:
- price: price_return_pct
- risk: volatility_20d
- quality: anomaly_rate_pct, quality_score
- nlp: sentiment_score
- ml: prediction_accuracy_pct
- operations: sla_compliance_pct, pipeline_duration_minutes

### Custom Report Builder
```
build_custom_report(metrics=[M001,M002], tickers=[AAPL,MSFT])
→ Loads pre-computed metrics from S3
→ Builds nested {ticker: {metric: value}} dict
→ Saves to S3: reports/custom/YYYY/MM/DD/
```

### Data Mesh API (data_mesh_api.py)
Access control workflow:
```
1. request_data_access()        → S3 access_requests/
2. approve_access_request()     → S3 approved/
3. get_data_product_sample()    → S3 sample data
4. publish_data_product_update() → S3 updates/
```

### Consumer Teams
| Team | Products | Use Case |
|---|---|---|
| ml_team | DP001 (prices) | Feature engineering |
| analytics | DP001, DP005 | Business reporting |
| trading | DP002, DP003, DP004 | Trading signals |
| risk | DP002 | Risk management |

## Compliance and Audit Layer

### Compliance Reporter (compliance_reporter.py)
Daily compliance checks across 4 frameworks:
```
CF001 SOX:      audit_trail + data_integrity + access_control + retention
CF002 GDPR:     pii_protection + data_minimization + erasure + consent
CF003 FINRA:    trade_reporting + audit_trail + retention + supervisory
CF004 INTERNAL: classification + quality_gates + sla + documentation
```

Output: `S3 reports/compliance/YYYY/MM/DD/report.json`
Certificates: `S3 reports/certificates/framework_id/date.json`

### Audit Manager (audit_manager.py)
8 audit categories logged throughout pipeline:
```
data_access → pipeline_execution → model_training → secret_access
schema_change → config_change → compliance_check → data_modification
```

Suspicious activity detection:
- 3+ failed attempts same actor → ALERT
- Access before 6 AM or after 10 PM → REVIEW

Output: `S3 audit/entries/YYYY/MM/DD/category/audit_id.json`
Summary: `S3 audit/summaries/YYYY/MM/DD/summary.json`

### Compliance → Audit → Certificate Flow
```
audit_manager logs all actions
      ↓
compliance_reporter checks requirements
      ↓
If all requirements met → generate_compliance_certificate()
      ↓
Certificate saved to S3 reports/certificates/
```

## Predictive Monitoring Layer

### Predictive Alerter (predictive_alerter.py)
3 predictive models run daily per ticker:

Model 1: Anomaly Probability
prices[-10:] → Z-score → sigmoid → probability
Alert if probability > 0.7

Model 2: Quality Degradation
quality_scores[-7:] → linear trend → days_until_breach
Alert if days_until_breach < 3

Model 3: SLA Risk
completion_times[-7:] → moving average → predicted_hour
Alert if predicted_hour > sla_target_hour

Output: S3 monitoring/predictive_alerts/YYYY/MM/DD/ticker.json

### Intelligent Monitor (intelligent_monitor.py)
correlate_metrics() → find metric relationships
detect_metric_anomaly() → Z-score on metric time series
generate_root_cause_hypothesis() → explain degradations
calculate_health_fingerprint() → MD5 of all metrics
compare_health_fingerprints() → detect state changes

Output: S3 monitoring/intelligent/YYYY/MM/DD/report.json

### Monitoring Stack (complete)
Layer 1: Real-time monitor (realtime_monitor.py) — every 5-15 min
Layer 2: Predictive alerter (predictive_alerter.py) — daily
Layer 3: Intelligent monitor (intelligent_monitor.py) — daily
Layer 4: Health dashboard (pipeline_health_dashboard.py) — daily

## Knowledge Graph and Search Layer

### Knowledge Graph (knowledge_graph.py)
Entities and relationships stored in S3:
```
knowledge_graph/entities/stock/AAPL.json
knowledge_graph/entities/sector/Technology.json
knowledge_graph/relationships/BELONGS_TO/rel_id.json
```

Built-in relationships:
5 tickers × BELONGS_TO × 3 sectors
2 COMPETES_WITH relationships (same sector)
2 CORRELATES_WITH relationships (high correlation)

Total: 5 entities + 9 relationships at startup

### Semantic Search (semantic_search.py)
Inverted index over pipeline documentation:
```
search/index/index.json → {term: [doc_ids]}
```

Searchable content:
- 99 module docstrings
- 79 ADR decisions
- README sections
- Pipeline overview content

### Integration
`knowledge_graph.find_connected_entities()`
→ identifies related stocks for portfolio analysis

`semantic_search.recommend_related_modules()`
→ developer productivity tool for finding related code

## Recommendation and Reporting Layer

### Stock Recommender (stock_recommender.py)
3 investor profiles with scoring:
```
conservative → quality > 90%, volatility < 15%
moderate     → quality > 80%, volatility < 25%
aggressive   → quality > 70%, volatility < 40%
```

Scoring: quality(40%) + volatility(30%) + sector(20%) + sentiment(10%)
Output: S3 reports/recommendations/YYYY/MM/DD/profile_name.json

### Pipeline Reports (pipeline_report_generator.py)
3 report types generated daily:
```
Executive Summary → business stakeholders
Technical Report  → engineering team
Weekly Digest     → trend analysis (Mondays)
```

Output: S3 reports/executive/, reports/technical/, reports/weekly/

### Report Consumers
| Report | Audience | Frequency | Format |
|---|---|---|---|
| Executive Summary | Business | Daily | HTML |
| Technical Report | Engineers | Daily | JSON + HTML |
| Weekly Digest | All teams | Weekly | HTML |
| Recommendations | Investors | Daily | JSON |

## MLOps Deployment Layer

### Model Deployment Manager (model_deployment_manager.py)
3-environment promotion pipeline:
```
Development (accuracy > 60%) → Staging (> 65%) → Production (> 70%)
```

Per deployment saved to S3:
```
deployments/development/anomaly_detector/deployment_id.json
deployments/staging/anomaly_detector/deployment_id.json
deployments/production/anomaly_detector/deployment_id.json
```

### Serving Infrastructure (serving_infrastructure.py)
Per-environment endpoints:
```
serving/endpoints/development/anomaly_detector.json
serving/endpoints/staging/anomaly_detector.json
serving/endpoints/production/anomaly_detector.json
```

Health check metrics per endpoint:
- healthy: bool
- latency_ms: float
- requests_per_minute: float
- error_rate_pct: float
- p95_latency_ms: float

### Complete MLOps Flow (updated)
```
Feature Engineering → AutoML → Hyperparameter Tuning
      ↓
Model Registry → Experiment Tracking → A/B Testing
      ↓
Drift Detection → Retraining Triggers → Model Monitor
      ↓
Deployment Manager (dev→staging→prod) → Serving Infrastructure
      ↓
REST API /predictions/{ticker} → Dashboard
```

## Data Validation and Contract Layer

### Pipeline Validator (pipeline_validator.py)
8 rules run on every batch of records:

```
Structural:   V001 schema_validation
Statistical:  V002 range_validation + V008 statistical_outliers
Relational:   V003 referential_integrity
Temporal:     V004 temporal_consistency
Business:     V005 business_rules
Completeness: V006 completeness_check
Uniqueness:   V007 uniqueness_check
```

Pass rate = passed_rules / 8 × 100
Output: S3 validation/YYYY/MM/DD/ticker.json

### Contract Enforcer (contract_enforcer.py)
C001 stock_price_event contract enforced per record:
```
enforce_contract() → violations found → blocked = True
                  → no violations   → pipeline continues
```

Violation tracking:
```
contracts/violations/YYYY/MM/DD/C001_AAPL.json
```

Contract health score:
```
health_score = 100 - (violations_this_week / total_records × 100)
```

### Validation → Contract → DLQ Flow
```
records → run_validation_suite() → pass_rate < 80% → WARNING
        → run_contract_enforcement() → blocked = True → DLQ
        → all good → proceed to PostgreSQL
```

## Workflow Automation Layer

### Automated Workflows (workflow_automation_engine.py)
5 workflows covering all pipeline cadences:

```
AW001 Daily (Mon-Fri 6 AM): 6 steps — core pipeline
AW002 Weekly (Mon 8 AM):    4 steps — model evaluation
AW003 Monthly (1st 9 AM):   3 steps — compliance
AW004 Continuous (every 15 min): 3 steps — quality monitor
AW005 Ad-hoc (manual):      3 steps — backfill
```

Execution tracking: S3 automation/executions/YYYY/MM/DD/
Reliability metrics: success_rate, avg_duration, failure_count

### Recovery Manager (pipeline_recovery_manager.py)
5 recovery strategies per failure:
```
retry      → backoff_seconds=60, max_attempts=3
skip       → continue without step result
fallback   → use alternative data source
checkpoint → resume from S3 checkpoint
manual     → pause for human review
```

Checkpoints saved to: S3 recovery/checkpoints/
Resilience score: auto_recovery_rate_pct

### Automation → Recovery → Alert Flow
```
Workflow execution → step failure detected
      ↓
handle_step_failure(strategy) → retry/skip/fallback
      ↓
If manual: pause_pipeline flag set → Slack alert
      ↓
Recovery recorded → resilience score updated
```

## Lakehouse Layer

### Medallion Architecture (lakehouse_manager.py)
3-tier storage with quality gates between layers:

```
Yahoo Finance API
      ↓
Bronze (raw) → Validate → Silver (clean) → Aggregate → Gold (business)
      ↓               ↓                          ↓
  Always          Only if                  Daily OHLCV
  written       score >= 80%              summaries
```

Layer paths:
```
lakehouse/bronze/YYYY/MM/DD/ticker/source_timestamp.json
lakehouse/silver/YYYY/MM/DD/ticker/validated_timestamp.json
lakehouse/gold/YYYY/MM/DD/ticker/aggregation_type.json
```

Retention: Bronze 365 days → Silver 730 days → Gold 1825 days

### Delta Versioner (delta_versioner.py)
Every write creates a transaction log entry:
```
delta/log/ticker/version_id_timestamp.json
```

Operations tracked: INSERT, UPDATE, DELETE, SCHEMA_CHANGE

Time travel: replay log up to target date
Optimization: compact files < 1KB weekly

### Lakehouse → Delta → Pipeline Flow
```
run_lakehouse_pipeline() → write_to_bronze() → create_delta_log_entry(INSERT)
      ↓
validation_score >= 80% → write_to_silver() → create_delta_log_entry(INSERT)
      ↓
aggregate → write_to_gold() → create_delta_log_entry(INSERT)
```

## Adaptive Modeling Layer

### Online Feature Engineer (online_feature_engineer.py)
Real-time features from rolling windows:
```
prices[-20:] → rolling stats (mean, std, momentum, acceleration)
volumes[-20:] → volume features (mean, ratio)
microstructure → spread proxy, price impact, trade intensity
regime → trending / volatile / mean_reverting
```

Output: S3 features/online/YYYY/MM/DD/ticker_timestamp.json

### Adaptive Model (adaptive_model.py)
Regime-based model selection:
```
trending      → gradient_boosting
volatile      → ensemble (RF + GB + Linear)
mean_reverting → linear_regression
```

Concept drift monitoring:
```
recent_errors vs baseline → drift_detected? → retrain/adjust/continue
```

Weight adaptation:
```
accuracy improves → increase model weight (learning_rate=0.01)
```

Output: S3 models/adaptive/YYYY/MM/DD/ticker.json

### Adaptive Pipeline Flow
```
new_price → online_features → regime_detection
         → model_selection → adaptive_prediction
         → concept_drift_check → weight_update
         → save_results
```

## Observability Layer

### Distributed Tracer (distributed_tracer.py)
Full pipeline execution tracing:
```
start_trace() → start_span(fetch_data) → end_span()
             → start_span(validate) → end_span()
             → start_span(detect_anomaly) → end_span()
             → start_span(predict) → end_span()
             → start_span(generate_insights) → end_span()
             → end_trace()
```

Storage: S3 traces/YYYY/MM/DD/trace_id/
Analysis: slowest_span, error_count, total_duration_ms

### Observability Dashboard (observability_dashboard.py)
Google SRE Golden Signals daily:
```
latency    → avg pipeline duration minutes
traffic    → records processed per hour
errors     → DLQ events / total events %
saturation → max(CPU, memory, disk) %
```

SLO Compliance (5 objectives):
```
pipeline_availability (99.5%) + data_freshness (25h)
quality_score (90%) + prediction_accuracy (70%)
api_latency (500ms p95)
```

Output: S3 reports/observability/YYYY/MM/DD/report.json

### Complete Observability Stack
```
Layer 1: Real-time monitor (every 5-15 min)
Layer 2: Distributed tracer (per pipeline run)
Layer 3: Golden signals (daily)
Layer 4: SLO compliance (daily)
Layer 5: Predictive alerts (daily)
Layer 6: Intelligent monitor (daily)
```
