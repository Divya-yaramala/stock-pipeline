# Forecasting Guide — Stock Pipeline

## Overview
The pipeline uses a multi-model forecasting approach combining
Prophet and Ensemble models with blending and scenario analysis.

## Forecasting Models

### Prophet (primary model — 60% weight)
- Algorithm: Facebook Prophet
- Strengths: trend + seasonality + holiday effects
- Best for: trending stocks with seasonal patterns
- Horizon: 5 trading days
- Confidence: 80% interval

### Ensemble (secondary model — 40% weight)
- Algorithm: RF + Gradient Boosting + Linear Regression
- Strengths: non-linear feature interactions
- Best for: volatile stocks with complex patterns
- Features: SMA, RSI, BB, MACD, volume, momentum

### Blended Forecast
Final prediction = Prophet × 0.6 + Ensemble × 0.4
Reduces individual model variance

## Scenario Forecasting

| Scenario | Formula | Description |
|---|---|---|
| Bull | base + 2×volatility | Optimistic case |
| Base | blended prediction | Most likely case |
| Bear | base - 2×volatility | Pessimistic case |

## Forecast Accuracy Metrics

| Metric | Formula | Target |
|---|---|---|
| MAE | mean(abs(pred - actual)) | < $5.00 |
| RMSE | sqrt(mean((pred-actual)²)) | < $7.00 |
| MAPE | mean(abs(pred-actual)/actual) × 100 | < 3% |
| Directional | % correct up/down prediction | > 55% |

## Time Series Analysis

### Volatility Regimes
| Regime | Daily Vol | Interpretation |
|---|---|---|
| Low | < 1% | Stable, trending |
| Medium | 1-2% | Normal market |
| High | > 2% | Volatile, uncertain |

### Trend Detection
Linear regression on last 20 days:
- uptrend: slope > 0, R² > 0.7
- downtrend: slope < 0, R² > 0.7
- sideways: R² < 0.7 (no clear trend)

## Running Forecasts
```bash
# Generate blended forecast
python -c "
from ingestion.forecast_enhancer import blend_forecasts, generate_scenario_forecasts
prophet = [185.0, 186.0, 187.0, 188.0, 189.0]
ensemble = [183.0, 184.0, 185.0, 186.0, 187.0]
blended = blend_forecasts(prophet, ensemble, prophet_weight=0.6)
scenarios = generate_scenario_forecasts(blended[0], volatility=3.5)
print('Blended day 1:', blended[0])
print('Scenarios:', scenarios)
"
```
