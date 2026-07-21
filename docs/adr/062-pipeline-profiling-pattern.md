# ADR 062 - Pipeline Profiling and Bottleneck Detection

## Status
Accepted

## Context
Needed systematic way to identify slow pipeline steps. Without profiling, engineers rely on anecdotal observation to find bottlenecks. Steps that are fast locally can become slow in production due to data volume, API rate limits, or network latency.

## Decision
Built pipeline optimizer with automatic bottleneck detection. Each pipeline step is timed using a wrapper function. Steps exceeding a configurable threshold are flagged as bottlenecks and paired with human-readable optimization recommendations saved to S3 for trending.

## Reasons
- 10-second threshold catches clearly slow steps without flagging acceptable latency
- Efficiency score gives single metric for pipeline health that can be tracked over time
- Recommendations are human-readable for quick action without requiring deep code knowledge
- Profiling results saved to S3 for trending and regression detection across pipeline runs
- Complements performance benchmarker from Day 69 with step-level rather than module-level detail

## Consequences
- Profiling adds overhead to pipeline run — negligible for I/O-bound steps but visible for CPU-bound
- 10s threshold may need tuning per environment — cloud environments vary in network latency
- Future: integrate with Datadog APM for production profiling with trace-level granularity
