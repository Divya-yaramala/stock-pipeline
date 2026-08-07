# 90-Day Journey — AI-Powered Stock Price Pipeline

A chronological record of building a production-grade ML pipeline from scratch.

---

## Phase 1: Foundation (Days 1–20)

**Goal:** Core data ingestion and storage.

| Day | Achievement |
|---|---|
| Day 1 | Project setup, S3 client, basic ingestion scaffold |
| Day 5 | Alpha Vantage API integration, OHLCV data fetch |
| Day 10 | Snowflake integration, data warehouse loading |
| Day 15 | PostgreSQL integration, dual-database writes |
| Day 20 | Data validation, schema enforcement, alerting |

**Key Decisions:**
- S3 as primary artifact store for portability
- Multi-database strategy (Snowflake + PostgreSQL) for flexibility
- Fail-fast validation at ingestion boundary

---

## Phase 2: Intelligence (Days 21–50)

**Goal:** ML models, predictions, and experiment tracking.

| Day | Achievement |
|---|---|
| Day 28 | Model registry (staging → production → archived) |
| Day 28 | Experiment tracker with hyperparameter logging |
| Day 32 | Feature engineering (OHLCV → 16 ML features) |
| Day 35 | Prophet forecasting model integration |
| Day 41 | Feature store (S3-backed per-ticker matrices) |
| Day 41 | Model serving endpoint |
| Day 44 | Model explainability (SHAP approximation) |
| Day 50 | Anomaly detection (Z-score + IQR + Isolation Forest) |

**Key Decisions:**
- Prophet for time-series due to seasonality handling
- SHAP approximation avoids heavy dependency on shap library
- Feature store enables reproducible training

---

## Phase 3: Reliability (Days 51–70)

**Goal:** Drift detection, retraining, monitoring, quality.

| Day | Achievement |
|---|---|
| Day 51 | Drift detection (PSI — Population Stability Index) |
| Day 51 | Retraining trigger (drift + schedule + performance) |
| Day 56 | Model monitoring (MAE/RMSE/MAPE/R2 daily tracking) |
| Day 56 | A/B testing (hash-based consistent assignment) |
| Day 60 | Data quality framework (completeness, freshness, accuracy) |
| Day 65 | Circuit breaker pattern (CLOSED/OPEN/HALF_OPEN) |
| Day 70 | AutoML pipeline (5 candidate models) |
| Day 70 | Hyperparameter tuning (GridSearchCV) |

**Key Decisions:**
- PSI threshold 0.2 triggers retraining (industry standard)
- Circuit breaker prevents cascade failures
- AutoML selects best algorithm per ticker

---

## Phase 4: Scale (Days 71–85)

**Goal:** Lakehouse, streaming, infrastructure.

| Day | Achievement |
|---|---|
| Day 75 | Delta-style lakehouse (bronze/silver/gold layers) |
| Day 78 | Streaming pipeline (real-time price ingestion) |
| Day 80 | Kafka integration (event-driven architecture) |
| Day 83 | Deployment manager (dev/staging/production envs) |
| Day 85 | Infrastructure as Code (Terraform modules) |

**Key Decisions:**
- Delta-style versioning without Spark dependency
- Medallion architecture enforces data quality tiers
- IaC enables reproducible cloud infrastructure

---

## Phase 5: Production Hardening (Days 86–89)

**Goal:** Observability, tracing, health checking, final polish.

| Day | Achievement |
|---|---|
| Day 86 | Delta Lake integration (ACID transactions, time travel) |
| Day 87 | Online feature engineering (rolling + microstructure + regime) |
| Day 87 | Adaptive modeling (regime-based model routing) |
| Day 88 | Distributed tracing (trace_id + span_id, S3 storage) |
| Day 88 | Observability dashboard (Google SRE Golden Signals + SLOs) |
| Day 89 | Pipeline health checker (A-F grading, 4 sub-checks) |
| Day 89 | Final README and world-class documentation |

**Key Decisions:**
- Online features enable sub-second latency inference
- Adaptive model routing improves accuracy per market regime
- Distributed tracing enables end-to-end debugging in production

---

## Day 90: Completion

**Final Stats:**
- 114+ ingestion modules
- 717+ tests
- 95 ADRs (Architecture Decision Records)
- 12 scripts
- 285+ design patterns

**What This Pipeline Can Do:**
1. Ingest real-time stock prices from Alpha Vantage
2. Validate, clean, and store in S3/Snowflake/PostgreSQL
3. Engineer 16+ ML features per ticker
4. Train and compare multiple ML models automatically
5. Detect data drift and trigger retraining
6. Serve live predictions with explainability
7. Monitor model performance with daily metrics
8. Run A/B tests to compare model variants
9. Process streaming data via Kafka
10. Store in medallion lakehouse with ACID guarantees
11. Trace every pipeline run end-to-end
12. Monitor SLOs and Golden Signals in production
13. Self-heal via circuit breakers and adaptive routing
14. Grade pipeline health automatically (A-F)

---

## Lessons Learned

**Technical:**
- S3 as the single source of truth simplifies distributed systems
- Type hints catch bugs before runtime — enforce from day one
- PSI is more robust than KS-test for production drift detection
- Online features require careful numerical stability (zero-division guards)

**Process:**
- ADRs are invaluable — writing the "why" prevents revisiting decisions
- Test-first thinking improves module design
- Documentation written alongside code stays accurate

**Architecture:**
- Start simple, add complexity only when the problem demands it
- Stateless modules with S3 persistence scale horizontally
- Observability is not optional — instrument from the start

---

*Built over 90 days as a portfolio demonstration of production ML engineering.*
