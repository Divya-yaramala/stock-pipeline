# ADR 001 - Why Apache Airflow over Prefect

## Status

Accepted

## Context

The pipeline needs a scheduler to trigger daily stock data ingestion after US market close (18:00 UTC on weekdays). The orchestrator must handle task dependencies, retry logic, and provide visibility into run history. The two strongest candidates evaluated were Apache Airflow 2.9 and Prefect 2.x.

## Decision

We chose Apache Airflow 2.9.

## Reasons

- **Industry adoption:** Airflow has significantly wider enterprise adoption. The majority of data engineering job postings explicitly list Airflow experience, making this project directly portfolio-relevant.
- **Community and ecosystem:** Airflow's community is larger, which means more third-party operators, plugins, and answered Stack Overflow questions when debugging.
- **Native integrations:** Airflow ships with built-in operators for AWS (S3, Redshift) and can be extended to Snowflake, reducing the need for custom integration code.
- **DAG complexity support:** Airflow's DAG model handles complex dependency graphs and conditional branching better than Prefect's flow model for multi-step batch pipelines.

## Consequences

- **Positive:** Strong portfolio signal; widely recognised in interviews and code reviews.
- **Negative:** Local setup requires Docker and several containers (webserver, scheduler, worker, postgres), consuming more memory than Prefect's lightweight server.
- **Negative:** Higher resource usage makes development on low-spec machines slower.
- **Negative:** Steeper initial learning curve — the DAG authoring model and XCom pattern are not intuitive for beginners.
