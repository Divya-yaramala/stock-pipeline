# Market Analytics Guide — Stock Pipeline

## Overview
The pipeline includes advanced market analytics covering
graph-based correlation analysis and sector rotation detection.

## Market Graph Analysis

### How It Works
1. Calculate pairwise Pearson correlations between all 5 tickers
2. Build graph: nodes=tickers, edges=correlations above threshold (0.7)
3. Calculate node centrality (degree / total connections)
4. Find connected clusters of similar-behaving stocks
5. Calculate graph density for systemic risk assessment

### Market Stability Interpretation
| Density | Stability | Risk Level | Meaning |
|---|---|---|---|
| < 0.3 | Stable | Low | Stocks moving independently |
| 0.3-0.7 | Moderate | Medium | Some correlation |
| >= 0.7 | Correlated | High | Systemic risk — all moving together |

### Market Leader
Ticker with highest centrality = most influential stock
In tech portfolios: usually AAPL or MSFT

### When Risk Is High
- All 5 tickers highly correlated (density > 0.7)
- Market crash risk: one stock falling pulls others down
- Action: increase diversification across sectors

## Sector Analysis

### Covered Sectors
| Ticker | Sector |
|---|---|
| AAPL | Technology |
| MSFT | Technology |
| GOOGL | Communication Services |
| AMZN | Consumer Discretionary |
| TSLA | Consumer Discretionary |

### Sector Benchmarks (annual target returns)
| Sector | Benchmark |
|---|---|
| Technology | 15% |
| Communication Services | 12% |
| Consumer Discretionary | 10% |

### Sector Rotation Signals
- Gaining: sector outperforming vs previous period → buy signal
- Losing: sector underperforming vs previous period → caution
- Stable: minimal change → hold

## Running Market Analytics
```bash
# Graph analysis
python -c "
from ingestion.market_graph_analyzer import calculate_market_stability, build_correlation_graph
corr = {'AAPL': {'AAPL': 1.0, 'MSFT': 0.85}, 'MSFT': {'AAPL': 0.85, 'MSFT': 1.0}}
graph = build_correlation_graph(corr, threshold=0.7)
stability = calculate_market_stability(graph)
print('Risk level:', stability['risk_level'])
"
```
