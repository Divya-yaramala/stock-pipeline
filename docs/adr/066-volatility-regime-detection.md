# ADR 066 - Volatility Regime Detection

## Status

Accepted

## Context

Needed to adapt forecasting strategy to market volatility — wide confidence intervals during
high-volatility periods, tighter intervals during low-volatility periods.

## Decision

Built 3-regime classifier using rolling standard deviation.

## Reasons

- Low volatility → tighter confidence intervals
- High volatility → wider intervals, scenario forecasts more important
- 20-day rolling window captures recent regime changes
- Three regimes match practitioner intuition
- Feeds into forecast_enhancer confidence interval calculation

## Consequences

- Regime boundaries (1%, 2%) may need tuning per stock
- Rolling window lags regime changes by up to 20 days
- Future: use GARCH model for more accurate volatility forecasting
