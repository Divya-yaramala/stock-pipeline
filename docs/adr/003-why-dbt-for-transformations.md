# ADR 003 - Why dbt over Custom SQL Scripts

## Status

Accepted

## Context

Raw stock data lands in a PostgreSQL staging schema and needs to be cleaned, typed, and aggregated into analytics-ready models before being served from Snowflake. The alternatives were writing plain SQL scripts executed by Python or Airflow BashOperators, or adopting dbt Core as a transformation framework.

## Decision

We chose dbt Core over writing custom SQL transformation scripts.

## Reasons

- **Built-in data quality tests:** dbt's `schema.yml` allows declarative tests (`not_null`, `unique`, `accepted_values`, `relationships`) that run after every model build, catching data issues before they reach analysts.
- **Automatic lineage documentation:** dbt generates a DAG of model dependencies that is visualisable via `dbt docs serve`, providing instant impact analysis when a source schema changes.
- **Version-controlled, modular SQL:** Each model is a standalone `.sql` file tracked in git. Models can reference each other via `{{ ref() }}`, making dependencies explicit and refactoring safe.
- **Industry standard:** dbt is the de facto transformation tool in the modern data stack. Proficiency with dbt is a common requirement in data engineering roles.

## Consequences

- **Positive:** Data quality issues are caught automatically on every run rather than discovered downstream.
- **Positive:** New team members can understand the transformation logic by reading model files and the lineage graph.
- **Negative:** Adds another tool with its own concepts (profiles, targets, materialisation strategies) that must be learned and maintained.
- **Negative:** Requires a `profiles.yml` to be configured correctly for each environment (local Postgres vs Snowflake), which can be a source of confusion.
- **Negative:** For very simple one-table transformations, dbt's setup overhead exceeds the value it provides compared to a single SQL file.
