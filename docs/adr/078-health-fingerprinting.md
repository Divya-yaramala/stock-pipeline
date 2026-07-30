# ADR 078 - Health Fingerprinting for State Change Detection

## Status
Accepted

## Context
Silent metric changes are hard to detect without constant comparison. Individual metric thresholds catch obvious regressions but miss subtle system-wide shifts where no single metric crosses its alert boundary yet the overall pipeline health has meaningfully changed.

## Decision
Built an MD5 health fingerprint computed from all current metric values. Comparing today's fingerprint against yesterday's instantly reveals whether any metric has changed, regardless of whether individual thresholds were crossed.

## Reasons
- Single hash represents entire pipeline health state — one comparison covers all metrics simultaneously
- Hash comparison detects any metric change instantly without scanning each metric individually
- MD5 is fast and sufficient for non-cryptographic use — we need change detection, not security
- Daily fingerprint comparison catches overnight changes before the next pipeline run begins
- Complements predictive alerting for comprehensive monitoring — predictive models catch trends, fingerprinting catches any discrete state change

## Consequences
- Hash changes on any metric change, even minor ones — may generate noise for small fluctuations
- Must store yesterday's fingerprint for comparison (S3 or local cache)
- MD5 collisions are theoretically possible but negligible for this use case
- Future: semantic fingerprinting to ignore insignificant changes (e.g., changes within ±1% of baseline)
