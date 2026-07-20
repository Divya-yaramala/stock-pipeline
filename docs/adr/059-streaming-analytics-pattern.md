# ADR 059 - Streaming Analytics with Sliding Windows

## Status
Accepted

## Context
Needed real-time analytics capabilities beyond batch processing. Batch pipelines compute indicators once daily and cannot detect intraday anomalies, momentum shifts, or real-time volume patterns. A lightweight streaming layer was required that integrates with the existing Python-first stack without introducing a heavy messaging broker dependency.

## Decision
Built sliding window analytics with deque-based implementation. The module processes price streams in memory using a fixed-size deque, computes Z-score anomaly detection on each tick, calculates RSI incrementally, and feeds a real-time OHLCV aggregator with VWAP and volume profile outputs.

## Reasons
- Python deque with maxlen automatically drops oldest values — no manual eviction logic needed
- Z-score anomaly detection works well for price streams where the distribution is approximately normal over short windows
- VWAP is industry-standard for intraday price analysis and used by institutional traders
- Volume profile shows price levels with most activity, revealing support and resistance zones
- Momentum detection complements technical indicators by giving a directional bias signal

## Consequences
- In-memory only (not persisted between runs) — window resets on each invocation
- Window size must be tuned per use case; too small increases false positives, too large adds lag
- Future: integrate with Kafka Streams for true real-time tick-by-tick processing
