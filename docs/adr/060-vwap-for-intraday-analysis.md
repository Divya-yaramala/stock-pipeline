# ADR 060 - VWAP for Intraday Price Analysis

## Status
Accepted

## Context
Needed fair value reference for intraday stock prices. Simple price averages ignore volume and can be misleading when a large trade moves price temporarily. An industry-standard metric was needed that reflects where most trading actually occurred.

## Decision
Implemented VWAP (Volume Weighted Average Price) as the key intraday metric in the real-time aggregator. VWAP weights each price by its traded volume, giving a volume-adjusted mean that reflects fair value for the trading session.

## Reasons
- VWAP is institutional standard for trade execution — buy below VWAP, sell above VWAP
- Price above VWAP = bullish intraday sentiment (buyers in control)
- Price below VWAP = bearish intraday sentiment (sellers in control)
- Simple to calculate: weighted mean by volume, no external libraries required
- Complements RSI and MACD from technical_indicators.py for a complete intraday picture

## Consequences
- VWAP resets daily (not useful across days) — anchored VWAP needed for multi-day analysis
- Requires volume data (not just price) — price-only feeds cannot compute VWAP
- Future: add anchored VWAP for longer-term analysis starting from a significant price event
