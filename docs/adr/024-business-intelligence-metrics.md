# ADR 024 - Business Intelligence Metrics

## Status
Accepted

## Context
The stock pipeline tracked raw prices, anomalies, and predictions, but lacked financial analytics
that portfolio managers and stakeholders expect. Basic price data alone does not answer questions
like "how much risk are we taking?" or "which sectors are outperforming?" We needed a BI layer
that converts raw prices into actionable financial metrics without adding heavyweight dependencies.

## Decision
Built a BI module (`ingestion/business_intelligence.py`) with Sharpe ratio, max drawdown, sector
performance grouping, and a market-cap weighted index. All metrics are computed in pure Python and
numpy, with results saved as JSON reports under `reports/bi/YYYY/MM/DD/` in S3 for downstream
consumption.

## Reasons
- Sharpe ratio is industry standard for risk-adjusted returns — widely understood by stakeholders
- Max drawdown shows worst-case loss scenario — essential for risk management conversations
- Sector performance enables portfolio diversification analysis across Technology and Consumer Cyclical
- Market-cap weighted index mirrors real index construction (e.g. S&P 500 methodology)
- All calculations done in pure Python/numpy — no external financial library dependencies

## Consequences
- Requires historical price data for accurate calculations — sparse S3 data falls back to defaults
- Sharpe ratio sensitive to time period chosen — results vary by lookback window
- Market caps must be manually updated — hardcoded values drift from real market capitalisation over time
