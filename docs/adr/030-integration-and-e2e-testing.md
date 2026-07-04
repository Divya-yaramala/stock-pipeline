# ADR 030 - Integration and E2E Testing Strategy

## Status
Accepted

## Context
Unit tests validate individual functions in isolation, but they don't catch failures that occur
at module boundaries — e.g., when fetch_stocks passes a DataFrame to data_validator, or when
the REST API serialises data from a mocked database connection. We needed a second and third tier
of tests to cover these boundaries without requiring a running infrastructure.

## Decision
Added integration tests (`tests/integration/`) for pipeline module flows and E2E tests
(`tests/e2e/`) for full API contracts. The CI pipeline runs all three tiers on every push.

## Reasons
- Integration tests catch module boundary failures that unit tests miss entirely
- E2E tests validate the full HTTP contract of all three APIs (REST, GraphQL, WebSocket)
- Separate test folders keep unit, integration, and E2E concerns cleanly separated
- CI runs all three test suites explicitly so failures are easy to attribute to a tier
- FastAPI's TestClient avoids needing a running server during CI

## Consequences
- Integration tests are slower than unit tests due to real ML model execution
- E2E tests require mocking database connections via dependency overrides
- CI pipeline takes longer — acceptable since integration and E2E are explicitly targeted steps
