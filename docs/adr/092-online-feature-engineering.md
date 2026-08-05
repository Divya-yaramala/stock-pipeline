# ADR 092 - Online Feature Engineering with Rolling Windows

## Status
Accepted

## Context
Batch feature engineering misses intraday market dynamics. The existing `feature_engineer.py` computes features from daily OHLCV data, but regime changes can happen within a trading session. The pipeline needed real-time feature computation that responds to the latest prices without a full retraining cycle.

## Decision
Built an online feature engineer computing features from rolling windows of recent prices and volumes. Features are computed on-demand from the last 20 data points, enabling real-time regime detection and model selection.

## Reasons
- Rolling window features update with every new price — no retraining needed for feature refresh
- Microstructure features capture market impact — bid-ask spread proxy and price impact enrich the feature set beyond daily OHLCV
- Regime features enable model selection — trending/volatile/mean-reverting routing to the best algorithm
- No retraining needed for feature updates — separates feature computation from model training
- Complements batch feature_engineer.py with real-time capability — daily batch for training, online for inference

## Consequences
- Window size (20) is fixed (not adaptive) — may miss long-horizon regime signals
- Microstructure features are proxies (not true bid/ask) — no Level 2 order book access
- Future: integrate with Level 2 order book data for true microstructure signals
