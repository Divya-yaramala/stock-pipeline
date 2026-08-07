# ADR 095 - Production Health Checking

## Status
Accepted

## Context
Needed an automated way to verify the pipeline is production-ready before deployment or after environment changes. Previously, health was assessed manually by checking logs and test results separately. A single composable check that covered all dimensions was missing.

## Decision
Built a pipeline health checker covering modules, tests, dependencies, and environment variables. The checker returns a single health score (0-100) with an A-F grade summarizing overall production readiness.

## Reasons
- Module import check catches circular imports and missing deps — surfaces problems before the pipeline runs
- Test suite health verifies all tests discoverable — confirms no collection errors hiding broken test files
- Dependency check catches version conflicts — detects packages missing from the environment early
- Env var check prevents runtime failures — confirms all secrets are loaded before any AWS/Snowflake calls
- Single health score (A-F) summarizes overall readiness — one number for dashboards and CI gates

## Consequences
- Health check itself takes 10-30 seconds to run — acceptable for pre-deployment gate, not for hot path
- Import check doesn't catch runtime errors — a module that imports but crashes at call time won't be flagged
- Future: add API health check and DB connectivity check to cover the full production dependency chain
