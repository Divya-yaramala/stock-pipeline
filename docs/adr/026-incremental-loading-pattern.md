# ADR 026 - Incremental Loading with Watermarks

## Status
Accepted

## Context
Needed efficient data loading without full refresh every day. Fetching all historical data on
each pipeline run was wasteful and would exhaust API rate limits quickly.

## Decision
Built watermark-based incremental loader with gap detection. Watermarks are stored in S3 as
JSON files per ticker and track the last successfully loaded date. A gap detector checks S3 for
missing daily files and returns only the dates that need backfilling.

## Reasons
- Watermarks track last successful load per ticker
- Gap detection finds missing dates automatically
- Only loads new data since last watermark
- S3 watermarks persist across pipeline restarts
- Reduces API calls by 90%+ on daily runs

## Consequences
- Watermarks must be manually reset for full backfill
- Gap detection limited to date granularity
- Requires reliable S3 for watermark storage
