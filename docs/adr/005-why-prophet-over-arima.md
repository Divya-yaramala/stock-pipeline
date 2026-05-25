# ADR 005 - Why Facebook Prophet over ARIMA

## Status

Accepted

## Context

We needed a time series forecasting model for stock price prediction. The model must produce next-day and multi-day closing price forecasts from 30 days of historical OHLCV data for five tickers, running nightly inside an Airflow DAG. Methods evaluated included Facebook Prophet, ARIMA/SARIMA, and LSTM-based recurrent networks.

## Decision

We chose Facebook Prophet over ARIMA.

## Reasons

- **Handles missing data automatically:** Prophet interpolates gaps internally without requiring the pre-processing steps (imputation, resampling) that ARIMA demands.
- **No need to manually check stationarity:** ARIMA requires differencing and ADF tests to confirm stationarity before fitting; Prophet fits directly on raw price series.
- **Built-in seasonality detection:** Prophet decomposes trend and seasonality automatically, making weekly trading patterns (e.g. Monday effects) discoverable without manual lag selection.
- **Easier to configure for non-statisticians:** Prophet exposes intuitive parameters (`changepoint_prior_scale`, `seasonality_mode`) rather than the (p, d, q) order selection that ARIMA requires.

## Consequences

- **Negative:** Less interpretable than ARIMA — ARIMA coefficients have direct statistical meaning; Prophet's decomposition is harder to audit.
- **Negative:** Slower training time on large datasets — Prophet fits a Stan model under the hood, which is slower than ARIMA's closed-form fitting for long histories.
- **Negative:** Facebook/Meta dependency — Prophet is maintained by Meta; long-term support and compatibility with future Python versions carries third-party risk.
