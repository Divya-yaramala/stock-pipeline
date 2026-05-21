# ADR 004 - Why Isolation Forest for Anomaly Detection

## Status

Accepted

## Context

The pipeline needs to flag unusual stock price movements automatically on a daily basis. The approach must work with a small rolling window of historical data (approximately 30 days), require no human-labelled training data, and be fast enough for daily batch processing across five tickers. Methods evaluated included Isolation Forest, Z-score thresholding, DBSCAN clustering, and LSTM autoencoders.

## Decision

We chose scikit-learn's Isolation Forest.

## Reasons

- **Small dataset compatibility:** Isolation Forest is effective with as few as 20–50 samples per feature, matching our 30-day rolling window without overfitting concerns that affect deep learning approaches.
- **Unsupervised — no labels needed:** Unlike supervised classifiers, Isolation Forest does not require historically labelled anomalies, which are expensive to produce for financial data.
- **Fast inference:** The algorithm isolates anomalies using random partitioning trees, giving O(n log n) training and O(log n) inference — well within the latency budget of a nightly batch job.
- **Multivariate support:** Isolation Forest natively handles the five OHLCV features (open, high, low, close, volume) together, capturing correlated anomalies that univariate Z-score checks would miss.

## Consequences

- **Positive:** No labelling effort required; the model is self-contained and runs without external dependencies beyond scikit-learn.
- **Negative:** The `contamination` hyperparameter (fraction of expected anomalies) requires manual tuning per ticker and market regime; a fixed value of 0.05 may over- or under-flag in volatile periods.
- **Negative:** Isolation Forest treats each day independently with no temporal awareness, so it cannot detect trend-based anomalies (e.g., a gradual multi-day drift that is individually unremarkable but collectively abnormal).
- **Negative:** Results are not easily explainable to non-technical stakeholders — the anomaly score is a relative isolation measure, not a human-readable signal.
