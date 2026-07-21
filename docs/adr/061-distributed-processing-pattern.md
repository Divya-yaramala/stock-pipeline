# ADR 061 - Distributed Processing with ThreadPoolExecutor

## Status
Accepted

## Context
Sequential ticker processing takes 5x longer than parallel. With 5 tickers each requiring fetch, validate, anomaly-detect, predict, and insight steps, the sequential pipeline spends most of its time waiting on I/O (S3 reads/writes, API calls). CPU is idle during these waits, leaving significant throughput on the table.

## Decision
Built distributed task manager using ThreadPoolExecutor from Python's standard library. Tasks are submitted to a thread pool with configurable worker count, executed concurrently, and results are collected with timing metadata for performance analysis.

## Reasons
- ThreadPoolExecutor is Python standard library — no additional dependencies required
- 5 workers matches 5 tickers for maximum parallelism across the ticker set
- Parallel S3 uploads reduce batch upload time by 80%+ for I/O-bound operations
- Task results include timing for performance analysis and bottleneck identification
- Chunk processing handles large datasets safely without memory spikes

## Consequences
- Thread safety required for shared resources — each task must use its own boto3 client
- GIL limits CPU-bound parallelism — ThreadPoolExecutor is best for I/O-bound tasks
- Future: migrate CPU-bound tasks (model training, feature engineering) to multiprocessing
