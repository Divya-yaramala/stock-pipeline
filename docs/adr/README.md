# Architecture Decision Records

This project follows the practice of Architecture Decision Records (ADRs) to document
the reasoning behind every major technology choice. Each ADR follows the format:
Status, Context, Decision, Reasons, and Consequences. This ensures future engineers
(and interviewers) understand not just WHAT was built but WHY.

Architecture Decision Records (ADRs) capture the key technical decisions made during the design and build of this project. Each ADR documents the context that prompted a decision, the decision itself, the alternatives considered, and the trade-offs accepted. They serve as a permanent record so that future contributors understand not just *what* was built but *why*.

## ADR Index

| # | Title | Status |
|---|-------|--------|
| [001](001-why-airflow-over-prefect.md) | Why Apache Airflow over Prefect | Accepted |
| [002](002-why-snowflake-over-redshift.md) | Why Snowflake over AWS Redshift | Accepted |
| [003](003-why-dbt-for-transformations.md) | Why dbt over custom SQL scripts | Accepted |
| [004](004-why-isolation-forest-for-anomaly-detection.md) | Why Isolation Forest for Anomaly Detection | Accepted |
| 005 | Why Prophet over ARIMA for price prediction | Accepted |
| [006](006-s3-cost-optimization-strategy.md) | S3 Cost Optimization Strategy | Accepted |
| [007](007-typed-config-with-dataclasses.md) | Typed Configuration with Python Dataclasses | Accepted |
| [008](008-ml-model-registry-pattern.md) | ML Model Registry Pattern | Accepted |
| [009](009-html-reports-with-jinja2.md) | HTML Reports with Jinja2 | Accepted |
| [010](010-technical-indicators-from-scratch.md) | Technical Indicators Built from Scratch | Accepted |
| [011](011-keyword-sentiment-vs-nlp.md) | Keyword Sentiment vs NLP Models | Accepted |
| [012](012-data-observability-pattern.md) | Data Observability Pattern | Accepted |
| [013](013-graphql-with-strawberry.md) | GraphQL API with Strawberry | Accepted |
| [014](014-websocket-for-realtime.md) | WebSocket for Real-Time Streaming | Accepted |
| [015](015-s3-caching-vs-redis.md) | S3 Caching vs Redis | Accepted |
| [017](017-data-governance-pattern.md) | Data Governance Pattern | Accepted |
| [018](018-feature-store-pattern.md) | S3-Based Feature Store | Accepted |
| [019](019-automated-testing-framework.md) | Automated Testing Framework | Accepted |
| [020](020-ensemble-models-pattern.md) | Ensemble Models over Single Model | Accepted |
| [021](021-chaos-engineering-pattern.md) | Chaos Engineering Pattern | Accepted |
| [022](022-secrets-management-pattern.md) | Secrets Management Pattern | Accepted |
| [023](023-workflow-management-pattern.md) | Workflow Management Pattern | Accepted |
| [024](024-business-intelligence-metrics.md) | Business Intelligence Metrics | Accepted |
| [025](025-property-based-testing.md) | Property-Based Testing Pattern | Accepted |
| [026](026-incremental-loading-pattern.md) | Incremental Loading with Watermarks | Accepted |
| [027](027-model-drift-detection.md) | Model Drift Detection with PSI | Accepted |
| [028](028-data-lineage-tracking.md) | Data Lineage Tracking | Accepted |
