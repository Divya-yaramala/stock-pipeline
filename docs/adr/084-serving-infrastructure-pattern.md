# ADR 084 - ML Model Serving Infrastructure

## Status
Accepted

## Context
Trained ML models need to be served reliably to the REST API and dashboard. Without a serving layer, predictions require re-running the full model pipeline on every request, which is slow and resource-intensive. A serving infrastructure abstracts model execution behind a managed endpoint.

## Decision
Built an endpoint management system with health checks, scaling configuration, and per-endpoint metrics tracking. Endpoints are per-environment (dev/staging/prod) and stored as configuration in S3.

## Reasons
- Per-environment endpoints isolate dev/staging/prod traffic — a broken dev endpoint cannot affect production
- Health checks detect endpoint failures before users notice degraded predictions
- Scaling capability handles load increases by adjusting replica count
- p95 latency tracking captures worst-case performance, not just average — important for SLA compliance
- S3-based endpoint config requires no additional infrastructure (no Kubernetes, no service mesh)

## Consequences
- Simulated endpoints — not actual HTTP servers yet (configuration only, no real listener)
- No load balancing between replicas — replica count is tracked but not enforced
- Health check latency is simulated with random values rather than measured from a real process
- Future: deploy as FastAPI endpoints on AWS ECS with real health check URLs and ALB load balancing
