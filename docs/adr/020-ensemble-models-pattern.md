# ADR 020 - Ensemble Models over Single Model

## Status

Accepted

## Context

The pipeline's price prediction layer relied on a single Facebook Prophet model per ticker. While Prophet handles seasonality and missing data well, a single model is constrained by its own assumptions and cannot capture the full range of patterns present in stock price data. More accurate predictions required combining multiple modelling approaches rather than betting on any one algorithm.

## Decision

Build an ensemble of three models in `ingestion/ensemble_model.py` — RandomForestRegressor, GradientBoostingRegressor, and LinearRegression — trained on the feature matrix produced by `ingestion/feature_engineer.py`. Predictions from all three are combined using a weighted average, with configurable per-ticker weights. Results and metrics are saved to S3 under `models/ensemble/YYYY/MM/DD/`.

## Reasons

- **Ensemble reduces variance and bias**: Averaging across models trained with different algorithms and inductive biases lowers the risk of any single model's systematic errors dominating the output.
- **Different models capture different patterns**: RF, Gradient Boosting, and Linear Regression each have different strengths — none dominates across all market conditions.
- **RF captures non-linear relationships**: RandomForest splits on feature thresholds and can model complex, non-linear interactions between technical indicators without explicit feature engineering for interactions.
- **Gradient Boosting handles complex interactions**: Sequentially correcting residuals allows GradientBoosting to fit patterns that neither RF nor Linear Regression can capture alone.
- **Linear Regression provides a stable baseline**: A linear model prevents the ensemble from overfitting on noise; its prediction anchors the average toward a simpler, lower-variance estimate.
- **Weighted averaging allows tuning per ticker**: High-volatility tickers (e.g. TSLA) can weight the non-linear models more heavily; stable tickers (e.g. MSFT) can lean on the linear baseline.

## Consequences

- **3x training time vs single model**: Training three models per ticker per day increases compute time proportionally — acceptable at 5 tickers but relevant at scale.
- **More complex to maintain and explain**: Three model objects, three prediction arrays, and a weighting scheme require more testing and documentation than a single-model pipeline.
- **Requires feature engineering pipeline**: Unlike Prophet which operates directly on time series, the ensemble depends on the feature matrix from `ingestion/feature_engineer.py` — if that step fails, the ensemble has no input.
