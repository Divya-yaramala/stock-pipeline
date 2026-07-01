# Loom Video Script — Stock Pipeline Demo

## Duration: 5-7 minutes

## Opening (30 seconds)
"Hi, I'm Divya Yaramala, an AI and Data Engineer based in New Jersey.
Today I'm going to walk you through my production-grade stock price
pipeline that I built over 52 days as part of my 90-day portfolio challenge."

## Architecture Overview (1 minute)
Show: docs/pipeline-overview.md
Talk about:
- Yahoo Finance → Airflow → dbt → Snowflake
- ML models: anomaly detection, forecasting, ensemble
- Three APIs: REST, GraphQL, WebSocket

## Live Code Walkthrough (2 minutes)
Show:
- ingestion/fetch_stocks.py (data ingestion)
- ingestion/anomaly_detector.py (ML model)
- api/main.py (REST API)
- airflow/dags/stock_pipeline_dag.py (orchestration)

## Tests and CI/CD (1 minute)
Show:
- pytest tests/ -v (371 tests passing)
- GitHub Actions green badges
- code-quality.yml workflow

## Key Stats (30 seconds)
- 371 tests passing
- 49 ingestion modules
- 28 ADRs
- 62 production patterns
- 3 APIs (REST + GraphQL + WebSocket)

## Closing (30 seconds)
"This project demonstrates my ability to build production-grade
data engineering systems from scratch. I'm actively looking for
Data Engineer and AI Engineer roles. Connect with me on LinkedIn!"
