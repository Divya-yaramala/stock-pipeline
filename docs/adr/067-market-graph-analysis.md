# ADR 067 - Market Graph Analysis for Correlation Detection

## Status

Accepted

## Context

Needed to understand market-wide correlation structure beyond pairwise metrics — specifically
to detect systemic risk and identify the most influential stocks in the portfolio.

## Decision

Built graph-based market analyzer with centrality and clustering using pure Python.

## Reasons

- Graph density reveals systemic risk (highly correlated markets)
- Node centrality identifies market leaders (most influential stocks)
- Clustering groups similar-behaving stocks
- Pure Python implementation (no networkx dependency)
- Complements existing Pearson correlation matrix

## Consequences

- Simple connected components algorithm (not spectral clustering)
- Threshold=0.7 may need tuning per market condition
- Future: use networkx for more sophisticated graph algorithms
