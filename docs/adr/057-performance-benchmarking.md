# ADR 057 — Performance Benchmarking Strategy

## Status
Accepted

## Context
The pipeline processes 5 tickers daily across 4 AI steps. As modules accumulate (75+), it becomes difficult to know whether a new change has made the pipeline slower. Without a systematic benchmark, performance regressions go undetected until they cause SLA misses.

## Decision
Built a performance benchmarker (`performance_benchmarker.py`) with:
- **S3 benchmarks**: put_object, get_object, list_objects_v2 — 5 runs each
- **Data processing benchmarks**: validation + feature engineering on 1000 dummy records, reporting records/second
- **10-run average** for function benchmarks to reduce noise
- **p95 latency** captures worst-case behavior (not just average)
- **20% regression threshold**: `compare_benchmarks` flags metrics that are >20% slower than baseline
- Results saved to `reports/benchmarks/YYYY/MM/DD/results.json`

## Reasons
1. **S3 benchmarks catch infrastructure slowdowns**: network issues or IAM policy changes show up as put/get latency spikes before they affect the pipeline
2. **Data processing benchmarks catch algorithm regressions**: an accidentally introduced O(n²) loop shows up immediately as a drop in records/second
3. **10-run average reduces noise**: single-run timing is unreliable; averaging over 10 runs gives stable baselines
4. **p95 latency**: mean latency masks tail latency — p95 captures the slowest 5% of calls, which is what matters for SLA compliance
5. **Baseline comparison**: `compare_benchmarks` produces actionable output (regressions / improvements / unchanged) rather than raw numbers

## Consequences
- Benchmark suite adds ~2 minutes to the full test suite if S3 is involved — run separately from unit tests in CI
- Baseline must be manually updated after deliberate performance improvements (otherwise it will always show as "improvement")
- S3 benchmarks require live AWS credentials — not runnable in CI without a test bucket
- Future: run benchmarks on every PR in CI using a dedicated test S3 bucket; alert if any metric regresses >20%
