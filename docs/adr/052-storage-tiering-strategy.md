# ADR 052 — Storage Tiering Strategy

## Status
Accepted

## Context
The pipeline accumulates data across multiple S3 prefixes over time. Raw stock prices, model predictions, anomaly records, and sentiment data all have different access patterns: recent data is queried daily by the dashboard and APIs, while data older than 90 days is rarely accessed. Keeping all data in S3 Standard storage pays a flat $0.023/GB regardless of access frequency, which becomes expensive as the dataset grows.

We needed a tiering strategy that reduces storage costs for cold data while keeping recent data immediately available.

## Decision
Implement a four-tier storage model mapped to AWS S3 storage classes:

| Tier   | S3 Class       | Cost/GB    | Use Case                        |
|--------|----------------|------------|---------------------------------|
| HOT    | STANDARD       | $0.023     | Data < 30 days old              |
| WARM   | STANDARD_IA    | $0.0125    | Data 30–90 days old             |
| COLD   | GLACIER        | $0.004     | Data 90–180 days old            |
| FROZEN | DEEP_ARCHIVE   | $0.00099   | Data > 180 days old             |

Two modules implement this:
- `data_archiver.py` — scans for archive/deletion candidates against `ARCHIVE_POLICIES`, executes Glacier copies and batch deletes, generates an archival report
- `storage_tier_manager.py` — inspects individual objects, recommends tier downgrades by age, executes moves, calculates per-tier cost breakdowns

Both modules support `dry_run=True` (default) so all operations can be previewed before execution.

## Reasons
1. **Cost reduction**: FROZEN costs 96% less than STANDARD for data that is never queried
2. **Dry-run safety**: Default `dry_run=True` prevents accidental data movement in production
3. **Batch deletion**: `delete_objects` with 1000-key batches matches the S3 API limit and reduces API call count
4. **Separation of concerns**: `data_archiver` handles policy-driven bulk operations; `storage_tier_manager` handles object-level inspection and recommendations

## Consequences
- Glacier and Deep Archive data has retrieval latency (minutes to hours) — not suitable for dashboards
- S3 Standard-IA has a 30-day minimum storage charge — moving objects that will be re-accessed within 30 days costs more, not less
- Archival reports are saved to S3 (`reports/archival/YYYY/MM/DD/`) for audit trail
- Weekly S3 optimizer (existing `s3_optimizer.py`) complements these modules — lifecycle policies at the bucket level are the long-term alternative
