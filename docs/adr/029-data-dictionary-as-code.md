# ADR 029 - Data Dictionary as Code

## Status
Accepted

## Context
As the pipeline grew to cover PostgreSQL, Snowflake, dbt models, and multiple S3 prefixes, we
needed a single source of truth for all data schemas. Without a maintained data dictionary,
new contributors had to reverse-engineer table structures from migration scripts or dbt models.

## Decision
Maintain the data dictionary as Markdown in docs/data-dictionary.md, version-controlled alongside
the rest of the codebase.

## Reasons
- Version controlled alongside code — schema changes are visible in pull requests
- Reviewable in PRs like any other change, enabling documentation review as part of code review
- No additional tools needed — works with any text editor and renders natively on GitHub
- Always up to date with actual schema when PR discipline is maintained
- Easy to link from README and reference in ADRs

## Consequences
- Manual updates required when schema changes — relies on contributor discipline
- No automatic validation against actual database schemas
- Future: generate automatically from dbt schema.yml using a script or dbt docs
