# ADR 025 - Property-Based Testing Pattern

## Status
Accepted

## Context
The pipeline test suite relied entirely on hand-crafted test cases with fixed input values. This
approach misses edge cases that only appear with unusual but valid inputs — prices near zero,
extreme volume spikes, or change percentages at alert thresholds. We needed a way to test
pipeline behaviour across a wide range of random inputs without writing hundreds of individual
test cases.

## Decision
Built a custom property-based testing module (`ingestion/property_tester.py`) that generates
random but valid stock price events and runs assertion checks across 100 samples per test run.
A companion edge case generator produces 7 fixed boundary condition events covering minimum
prices, maximum prices, zero volume, and alert threshold percentages. Results are saved to S3
under `testing/property/YYYY/MM/DD/` for trend tracking over time.

## Reasons
- Finds edge cases that manual tests miss — random sampling surfaces unexpected failures
- 100 random samples per test run provide meaningful coverage without being exhaustive
- 7 boundary condition events cover the most likely failure points explicitly
- No additional libraries needed — implemented without Hypothesis or other frameworks
- Results saved to S3 for trending — pass rate history enables regression detection

## Consequences
- Tests are non-deterministic — failures may not reproduce without a fixed random seed
- Slower than unit tests — 100 samples per run adds latency to the test suite
- Must tune sample count for CI speed vs coverage — higher counts increase confidence but slow CI
