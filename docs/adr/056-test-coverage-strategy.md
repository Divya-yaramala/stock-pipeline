# ADR 056 — Test Coverage Strategy

## Status
Accepted

## Context
The pipeline has 465+ passing tests but no mechanism to track which code paths are actually exercised. Without coverage tracking, it is possible to have many tests that all hit the same happy-path code while entire modules (error handling, edge cases, remediation paths) go untested. A growing codebase also risks coverage declining as new modules are added without corresponding tests.

## Decision
Built a test coverage reporter (`test_coverage_reporter.py`) using `pytest-cov` with the following design:
- **80% threshold**: files below this level are surfaced as low-coverage
- **7-day trend analysis**: coverage reports saved to S3 daily; `compare_coverage_trend` detects improving/stable/declining trends
- **HTML report**: `generate_coverage_report_html` produces a shareable summary
- **S3 storage**: reports saved to `reports/coverage/YYYY/MM/DD/coverage.json`

## Reasons
1. **pytest-cov is the ecosystem standard**: integrates natively with pytest, generates `coverage.json` that is easy to parse
2. **80% threshold**: catches undertested modules without being so strict it blocks progress; critical modules can have custom thresholds in the future
3. **Trend tracking**: a single coverage number is less informative than knowing whether it is going up or down over the past week
4. **HTML report**: human-readable summary for code review and stakeholder reporting
5. **S3 storage**: durable, date-stamped reports enable 7-day trend comparison

## Consequences
- Coverage run adds ~30 seconds to the CI pipeline — acceptable for the insight gained
- 80% threshold may be too low for safety-critical modules (e.g. `pii_detector.py`, `secrets_manager.py`) — future gate can set per-module thresholds
- `coverage.json` must exist before `run_coverage_report` can parse it — subprocess failure returns empty data gracefully
- Future: enforce coverage gate in CI — block PR merge if total coverage drops below 80%
