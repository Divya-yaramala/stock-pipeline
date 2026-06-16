# ADR 013 - GraphQL API with Strawberry

## Status

Accepted

## Context

The pipeline already exposed a REST API for querying stock prices, anomalies, and predictions. As the number of data types grew, REST clients were forced to either over-fetch (receiving fields they didn't need) or make multiple round-trips. A more flexible query interface was needed alongside REST.

## Decision

Build a GraphQL API using the Strawberry framework in `api/graphql_api.py`, mounted on a separate FastAPI app running on port 8001.

## Reasons

- **Strawberry uses Python type hints natively**: Schema types are defined as regular Python dataclasses decorated with `@strawberry.type`, so there is no separate SDL schema file to keep in sync with the code.
- **Auto-generates GraphQL schema from Python classes**: Strawberry introspects the type annotations and generates the full GraphQL schema automatically, enforcing consistency between Python and GraphQL types.
- **Interactive playground built-in at /graphql**: Strawberry ships with GraphiQL, giving developers an in-browser IDE for exploring and testing queries with no extra tooling.
- **Type safety enforced at compile time**: Because schema types are Python dataclasses, mypy and type checkers catch field mismatches before runtime.
- **Clients can request exactly the fields they need**: GraphQL's selection sets let API consumers fetch only the fields relevant to their use case, reducing payload size and avoiding over-fetching.

## Consequences

- **Additional API to maintain alongside REST**: Two APIs expose similar data; changes to the data model must be reflected in both.
- **Learning curve for GraphQL query syntax**: Team members unfamiliar with GraphQL must learn query syntax, fragments, and resolver conventions.
- **Two separate ports (8000 REST, 8001 GraphQL)**: Operations and Docker Compose must manage two API services; clients must know which port to target.
