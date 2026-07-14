# ADR 046 - Data Mesh Pattern

## Status

Accepted

## Context

As the stock pipeline grew to include ML insights, NLP analysis, and analytics domains, a single-team ownership model became a bottleneck. Each data consumer (trading, risk, analytics, executives) had different SLA requirements and quality expectations. A domain-driven approach was needed to assign clear ownership and accountability per data product.

## Decision

Implemented a data mesh pattern with 5 data products organized across 4 business domains:

| Product ID | Name | Domain | Owner |
|---|---|---|---|
| DP001 | stock_prices | market_data | data_engineering |
| DP002 | anomaly_signals | ml_insights | ml_team |
| DP003 | price_forecasts | ml_insights | ml_team |
| DP004 | market_sentiment | nlp_insights | data_engineering |
| DP005 | portfolio_analytics | analytics | analytics_team |

Each product is registered in S3 under `data_mesh/products/` and tracked with health scores.

## Reasons

- **Data products have clear owners and consumers** — each product declares its owner team and downstream consumers explicitly
- **SLA per product** — each product has its own SLA (hours) rather than a single pipeline-level SLA
- **Domain grouping mirrors business structure** — market_data, ml_insights, nlp_insights, and analytics map directly to team boundaries
- **Health scores per product** — track quality independently per domain rather than a single pipeline score
- **Event bus decouples pipeline stages** — 10 event types allow stages to communicate without tight coupling

## Consequences

- More complex ownership model than a single-team pipeline — requires clear team contracts
- Cross-team coordination required for consumer SLAs (e.g., trading team depends on ml_team's anomaly_signals)
- Products stored in S3 as JSON — lightweight but not a full data catalog; acceptable for portfolio scale
- Future: implement data product APIs so consumers can self-serve without direct S3 access
