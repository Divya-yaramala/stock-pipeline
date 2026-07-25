# ADR 069 - VaR and CVaR for Risk Management

## Status

Accepted

## Context

Needed quantitative risk metrics beyond simple volatility to support portfolio risk reporting
and compliance-ready risk summaries.

## Decision

Implemented historical VaR and CVaR at 95% confidence.

## Reasons

- VaR is industry standard for risk reporting
- CVaR (Expected Shortfall) is more robust than VaR for tail risk
- Historical simulation avoids normal distribution assumption
- 95% confidence = 1-in-20 day loss threshold
- Portfolio VaR combines individual risks with weights

## Consequences

- Historical VaR requires sufficient data (30+ days)
- Does not capture black swan events beyond history
- Future: add Monte Carlo VaR for forward-looking risk
