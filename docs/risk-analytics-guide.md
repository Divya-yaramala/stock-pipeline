# Risk Analytics Guide — Stock Pipeline

## Overview
The pipeline includes institutional-grade risk metrics
used by hedge funds and asset managers.

## Risk Metrics

### Value at Risk (VaR)
VaR 95% = the loss you should not exceed on 95% of trading days
Example: VaR = -2.5% means on 95% of days loss < 2.5%
On 5% of days (1 in 20) loss could exceed 2.5%

### Conditional VaR (CVaR / Expected Shortfall)
CVaR = average loss on the worst 5% of days
Always more negative than VaR
Better measure of tail risk than VaR alone

### Annualized Volatility
Daily volatility × sqrt(252)
< 15%: low volatility
15-30%: medium volatility
> 30%: high volatility

### Risk Level Classification
| Level | Annual Vol | VaR 95% |
|---|---|---|
| LOW | < 15% | > -1.5% |
| MEDIUM | 15-25% | > -2.5% |
| HIGH | 25-40% | > -4% |
| VERY_HIGH | > 40% | < -4% |

## Portfolio Optimization

### Efficient Frontier
100 random weight combinations plotted as:
X-axis: Portfolio volatility (risk)
Y-axis: Expected return

### Key Portfolios
- Max Sharpe: best risk-adjusted return
- Min Volatility: lowest risk regardless of return

### Sharpe Ratio
Sharpe = (return - risk_free_rate) / volatility
risk_free_rate = 5% (10-year Treasury)
Sharpe > 1.0: good
Sharpe > 2.0: excellent

### Rebalancing Trades
When to rebalance:
- Any weight drifts > 5% from target
- Quarterly scheduled rebalancing
- After significant market move (>10%)

## Interpreting Results
High portfolio VaR (< -3%):
- Consider reducing position sizes
- Add defensive assets (bonds, gold)
- Increase diversification across sectors

Max Sharpe portfolio suggests:
- Overweight AAPL and MSFT (highest Sharpe historically)
- Underweight TSLA (highest volatility, lower Sharpe)

## Risk Commands
```bash
# Quick VaR check
python -c "
from ingestion.risk_analyzer import calculate_var
returns = [-0.02, 0.01, -0.03, 0.005, -0.015, 0.02, -0.01, 0.03, -0.025, 0.015]
print('VaR 95%:', calculate_var(returns))
"
```
