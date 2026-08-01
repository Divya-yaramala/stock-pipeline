# ADR 083 - Model Deployment Environments

## Status
Accepted

## Context
ML models need a structured promotion path to production. Pushing a newly trained model directly to production without validation gates risks degraded user-facing predictions. A controlled environment progression ensures only models meeting accuracy thresholds reach production.

## Decision
Implemented a 3-environment deployment pipeline (development → staging → production) with minimum accuracy gates at each level and rollback capability to restore a previous version if a new deployment regresses.

## Reasons
- 3 environments match standard software delivery practice — familiar to any engineer
- Minimum accuracy gates (60% dev / 65% staging / 70% prod) prevent poor models reaching production
- Rollback capability reduces deployment risk — any failed promotion can be undone
- Deployment history stored in S3 provides a full audit trail of what ran in each environment
- Serving endpoints track per-environment model usage and health

## Consequences
- Manual promotion required — `promote_to_environment()` must be called explicitly (no auto-promote yet)
- Minimum accuracy thresholds may block valid models temporarily if metric calculation differs between envs
- S3-based deployment registry is simple but not a real model registry (no versioning metadata)
- Future: implement blue-green deployment for zero-downtime production updates
