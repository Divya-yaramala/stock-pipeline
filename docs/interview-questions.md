# Interview Q&A — Stock Pipeline

## Architecture Questions

Q: Walk me through your pipeline architecture.
A: The pipeline has 3 main layers:
   1. Ingestion: Yahoo Finance → Airflow → PostgreSQL + S3
   2. Processing: dbt transformations → Snowflake warehouse
   3. Serving: REST + GraphQL + WebSocket APIs + Streamlit dashboard
   Plus: Full MLOps lifecycle with 15 stages from features to deployment.

Q: Why Airflow over other orchestrators?
A: See ADR 001 — Airflow has broader adoption, better UI for monitoring,
   native dbt integration, and retry logic built-in.

Q: How do you handle pipeline failures?
A: Three mechanisms:
   1. Dead letter queue captures failed records to S3 errors/
   2. Retry logic with tenacity (exponential backoff)
   3. Pipeline recovery manager with 5 strategies (retry/skip/fallback/checkpoint/manual)

## ML/AI Questions

Q: How do you detect stock price anomalies?
A: Isolation Forest — an unsupervised algorithm that scores points
   by how easily they can be isolated. Anomaly score < threshold → anomaly.
   Also: Z-score streaming anomaly detection for real-time.

Q: How do you know when your model needs retraining?
A: Two signals:
   1. PSI-based drift detection: feature distributions shift → retrain
   2. Performance degradation: RMSE increases 20%+ vs baseline → retrain

Q: What is your forecasting approach?
A: Blended model: Prophet (60%) + Ensemble (40%)
   Prophet captures trend + seasonality. Ensemble captures non-linear features.
   Weighted blend reduces individual model variance.

## Data Engineering Questions

Q: How do you ensure data quality?
A: Four layers:
   1. 8-rule validation suite (schema, ranges, business rules, temporal)
   2. Quality gates (5 gates that block pipeline on failure)
   3. Data contracts (schema agreements with enforcement)
   4. Quality scoring (A-F grade per ticker daily)

Q: How do you handle incremental loading?
A: Watermark-based tracking — each ticker stores last_loaded_date.
   Gap detection finds missing dates automatically.
   Only new data since last watermark is fetched.

Q: What is your data lineage approach?
A: Custom lineage tracker records source → target relationships.
   Impact analysis shows downstream effects of schema changes.
   94 ADRs document every major architectural decision.
