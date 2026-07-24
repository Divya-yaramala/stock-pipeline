# ADR 068 - Sector Rotation Detection

## Status

Accepted

## Context

Needed to identify which sectors are gaining or losing momentum to support portfolio
rebalancing decisions and spot institutional trading patterns.

## Decision

Built week-over-week sector rotation detector.

## Reasons

- Sector rotation is key institutional trading signal
- Week-over-week comparison captures medium-term momentum
- Simple gaining/losing/stable classification is actionable
- Benchmark alpha shows outperformance vs market
- Complements individual ticker analysis

## Consequences

- Only 3 sectors covered (5 tickers is limiting)
- Week-over-week may miss monthly rotation patterns
- Future: add more tickers per sector for better coverage
