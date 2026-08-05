# ADR 091 - Online Learning and Adaptive Modeling

## Status
Accepted

## Context
Static batch models miss regime changes in market conditions. A model trained on calm trending data performs poorly during volatile periods. The pipeline needed a way to adapt model selection and weights dynamically without full retraining cycles.

## Decision
Built an adaptive model with regime detection and online features. Rolling window features are computed from recent prices and volumes without retraining. The system detects the current market regime and selects the best model accordingly, adjusting weights based on recent accuracy.

## Reasons
- Market regimes (trending/volatile/mean-reverting) require different models — gradient boosting for trends, ensemble for volatility, linear for mean-reversion
- Online features computed from rolling windows without retraining — enables real-time feature updates
- Weight adaptation responds to accuracy changes gradually — avoids overcorrection from single bad predictions
- Concept drift detection triggers retraining proactively — catches distribution shift before degradation compounds
- Microstructure features capture intraday market dynamics — spread proxy and price impact enrich the feature set

## Consequences
- More complex than single static model — regime classification adds a decision layer
- Regime classification may be noisy in sideways markets — confidence score mitigates but does not eliminate this
- Future: implement true online learning with SGD updates for parameter-level adaptation without full retraining
