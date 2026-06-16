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
