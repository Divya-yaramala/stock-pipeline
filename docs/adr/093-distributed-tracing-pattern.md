# ADR 093 - Distributed Tracing for Pipeline Observability

## Status
Accepted

## Context
Needed end-to-end visibility into pipeline execution across steps. When a pipeline run takes longer than expected or silently fails a step, there was no way to identify which specific step was slow or erroring without reading through log files manually.

## Decision
Built a custom distributed tracer with traces and spans. Each pipeline run creates a trace with a unique trace_id, and each step (fetch_data, validate, detect_anomaly, predict, generate_insights) creates a child span. Span timings and statuses are saved to S3 for post-run analysis.

## Reasons
- Traces capture full pipeline execution timeline — single source of truth for run history
- Spans identify slowest steps automatically — `analyze_trace` surfaces the bottleneck without log parsing
- Error spans enable targeted debugging — filter by status="error" to find failures instantly
- S3-based storage requires no Jaeger/Zipkin infrastructure — lightweight for a daily batch pipeline
- Google SRE golden signals provide standardized metrics — latency, traffic, errors, saturation cover all SRE pillars

## Consequences
- Manual span instrumentation required per step — each new step must call start_span/end_span explicitly
- S3 lookup needed to reconstruct full trace — get_trace paginates S3 rather than querying a trace backend
- Future: integrate with AWS X-Ray for production tracing with auto-instrumentation and flame graphs
