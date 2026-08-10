# Lessons Learned — 90-Day Portfolio Challenge

## Technical Lessons

### 1. Type Hints From Day 1
mypy caught 200+ potential runtime errors during development.
Always use Optional[str] = None not str = None for optional params.
Cast dict values: str(d["key"]), float(str(d["key"]))

### 2. Tests Are Documentation
717+ tests serve as living documentation of expected behavior.
When unsure how a function works → read the tests.
Property-based tests found edge cases manual tests missed.

### 3. ADRs Prevent Revisiting Decisions
96 ADRs saved hours of re-debating same decisions.
"Why did we choose S3 over Redis?" → ADR 015 answers it.
Write the ADR before implementing, not after.

### 4. Graceful Degradation Everywhere
Every external call (S3, API, DB) has try/except.
Never let Slack failure break the main pipeline.
Return None/False/empty list instead of raising exceptions.

### 5. CI/CD Discipline From Day 1
Green badges forced immediate fixes (no debt accumulation).
mypy + black + isort + flake8 caught issues before merge.
Integration tests caught failures that unit tests missed.

## Process Lessons

### 6. Daily Commits Create Accountability
90 consecutive days of commits required daily discipline.
Even on busy days: doc commits keep the streak alive.
Green contribution graph is visible proof of consistency.

### 7. Documentation Is Half the Work
README, runbook, guides, ADRs = as important as code.
Recruiters read README before looking at code.
Operational runbooks prevent 3 AM incidents.

### 8. Start Simple, Layer Complexity
Day 1: basic fetch + validate + store
Day 90: MLOps + lakehouse + observability + compliance
Each layer built on the previous — never skipped steps.

## Career Lessons

### 9. Portfolio Projects Must Be Real
No toy datasets — used real Yahoo Finance + CoinGecko APIs.
No fake CI/CD — real GitHub Actions running on every push.
No placeholder tests — 717+ real assertions.

### 10. Architecture Decisions Matter
Not just "it works" but "why did we choose this approach?"
96 ADRs demonstrate senior engineering thinking.
Trade-off awareness separates good engineers from great ones.
