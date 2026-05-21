# ADR 002 - Why Snowflake over AWS Redshift

## Status

Accepted

## Context

The pipeline needs a cloud data warehouse to store analytics-ready tables produced by dbt. The warehouse must support SQL-based querying, integrate cleanly with dbt, and be feasible to set up without an existing cloud infrastructure commitment. The two main candidates were Snowflake and AWS Redshift.

## Decision

We chose Snowflake.

## Reasons

- **Compute/storage separation:** Snowflake decouples compute (virtual warehouses) from storage, allowing the warehouse to be paused when idle and resumed on demand. This keeps costs near zero for a dev/portfolio project with infrequent query loads.
- **dbt integration:** Snowflake is the primary target dbt was designed for. The `dbt-snowflake` adapter is mature, well-documented, and supports all dbt features including incremental models and snapshots.
- **No infrastructure dependency:** Redshift requires an existing AWS VPC, subnet groups, and security group configuration. Snowflake provides a standalone SaaS account that can be created in minutes with a free trial tier.
- **Analytical query performance:** Snowflake's columnar storage and automatic query optimisation deliver fast results on ad-hoc analytical queries without manual cluster tuning.

## Consequences

- **Positive:** Faster setup and lower operational overhead compared to Redshift.
- **Negative:** Adds a second vendor outside the AWS ecosystem, introducing a separate billing account and login.
- **Negative:** Snowflake-specific SQL features (e.g., `CLUSTER BY`, `TIMESTAMP_NTZ`, `AUTOINCREMENT`) are not portable to other warehouses without modification.
- **Negative:** Free trial credits expire; sustained use requires a paid account.
