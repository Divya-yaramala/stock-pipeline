# ADR 070 - Efficient Frontier Portfolio Optimization

## Status

Accepted

## Context

Needed a quantitative approach to portfolio weight optimization that is actionable without
requiring complex mathematical solvers.

## Decision

Built Monte Carlo efficient frontier with 100 random portfolios.

## Reasons

- Monte Carlo avoids complex quadratic programming
- 100 portfolios sufficient to approximate the frontier
- Max Sharpe portfolio is directly actionable
- Min volatility portfolio for risk-averse strategies
- Rebalancing trades make optimization actionable

## Consequences

- Monte Carlo is approximate (not exact optimal)
- 100 portfolios may miss the true optimal for small differences
- Future: use scipy.optimize for exact mean-variance optimization
