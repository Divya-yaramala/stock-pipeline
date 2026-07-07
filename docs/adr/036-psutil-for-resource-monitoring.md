# ADR 036 - psutil for System Resource Monitoring

## Status
Accepted

## Context
The pipeline needed lightweight system resource monitoring to check CPU, memory, and disk
usage before each run. The check prevents pipeline execution when the host is already under
pressure — avoiding OOM kills or disk-full failures mid-run.

## Decision
Use the `psutil` library to collect CPU percentage, virtual memory percentage, and disk
usage percentage. Thresholds (CPU 80%, memory 85%, disk 90%) gate pipeline execution.

## Reasons
- Pure Python, cross-platform (Windows + Linux + Mac)
- No system daemon or privileged access needed
- Lightweight — minimal CPU overhead for a single check
- Returns clean numeric values that map directly to thresholds
- Works inside Docker containers without special mounts
- Already a transitive dependency in the ecosystem (used by Airflow workers)

## Consequences
- Only monitors the local machine — not suitable for distributed or multi-node setups
- No built-in historical trending — each call is a point-in-time snapshot
- psutil disk_usage("/") uses root path — may need adjustment on Windows
- Future: ship metrics to CloudWatch for trending and alerting over time
