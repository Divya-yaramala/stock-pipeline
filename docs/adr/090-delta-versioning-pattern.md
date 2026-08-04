# ADR 090 - Delta Versioning with Transaction Log

## Status
Accepted

## Context
Needed table versioning and time travel without adding the Delta Lake library. Delta Lake requires Spark, which is a heavyweight dependency for a daily batch pipeline running on a single server. The pipeline needed version history and the ability to reconstruct past table states for debugging and data recovery.

## Decision
Built a custom delta versioner using S3 transaction logs. Each write operation creates a lightweight JSON log entry storing the operation type, record counts, and schema change flag. Time travel replays the log up to the target date.

## Reasons
- Delta Lake requires Spark (heavy dependency — adds 500MB+ to runtime, incompatible with our FastAPI environment)
- Custom S3 log sufficient for daily batch pipeline — our data volume is small (5 tickers × 1 record/day)
- Time travel reconstructs historical table state — enables data recovery without backups
- Optimization compacts small files for cost efficiency — reduces S3 request overhead weekly
- Transaction log provides complete change history — every INSERT, UPDATE, DELETE is auditable

## Consequences
- Not ACID compliant (no true transactions) — concurrent writes could create inconsistent logs
- Time travel requires replaying full log (slow for large tables) — acceptable for our daily batch volume
- Schema evolution is tracked as a flag but not enforced — no automatic schema migration
- Future: migrate to Apache Iceberg for production ACID compliance and efficient time travel
