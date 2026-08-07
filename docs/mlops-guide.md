# MLOps Guide — AI-Powered Stock Price Pipeline

This document covers the end-to-end MLOps lifecycle implemented in the pipeline: model training,
registration, experiment tracking, serving, monitoring, drift detection, and automated retraining.

---

## MLOps Architecture

```
Data → Feature Engineering → Training → Registry → Serving
                                ↓
                       Experiment Tracker
                                ↓
                       Model Monitor → Drift Detector → Retraining Trigger
                                ↓
                       A/B Tester → Winner → Promote to Production
```

---

## 1. Feature Engineering (`ingestion/feature_engineer.py`)

Builds ML-ready feature matrices from raw OHLCV data.

| Feature Group | Features |
|---|---|
| Price | open, high, low, close, price_range, price_change_pct |
| Volume | volume, volume_change_pct |
| Momentum | price_momentum_5d, price_momentum_10d |
| Technical | SMA_5, SMA_20, RSI_14, BB_upper, BB_lower, MACD |

```bash
python -c "from ingestion.feature_engineer import engineer_features; import os; print(engineer_features('AAPL', os.getenv('AWS_BUCKET_NAME')))"
```

---

## 2. Feature Store (`ingestion/feature_store.py`)

S3-backed store for saving and retrieving feature matrices per ticker.

| Operation | S3 Path |
|---|---|
| Save features | `features/YYYY/MM/DD/{ticker}.json` |
| Load features | `features/YYYY/MM/DD/{ticker}.json` |
| Feature groups | `features/groups/{group_name}.json` |

```bash
python -c "from ingestion.feature_store import save_features; import os; print('Feature store ready')"
```

---

## 3. Model Training

Two training paths are supported:

### Single Model (`ingestion/model_comparator.py`)
Trains Random Forest vs Linear Regression, selects the winner by RMSE.

### Ensemble Model (`ingestion/ensemble_model.py`)
Combines Random Forest + Gradient Boosting + Linear Regression with weighted averaging.

```bash
python -c "from ingestion.model_comparator import run_model_comparison; import os; print(run_model_comparison('AAPL', os.getenv('AWS_BUCKET_NAME')))"
```

---

## 4. Experiment Tracking (`ingestion/experiment_tracker.py`)

Records hyperparameters and metrics for every training run.

| Field | Description |
|---|---|
| experiment_id | Unique run identifier |
| model_type | e.g. random_forest, prophet, ensemble |
| params | Hyperparameter dict |
| metrics | MAE, RMSE, MAPE, R2 |
| run_at | ISO timestamp |

```bash
python -c "from ingestion.experiment_tracker import log_experiment; import os; print('Experiment tracker ready')"
```

---

## 5. Model Registry (`ingestion/model_registry.py`)

Lifecycle: `staging` → `production` → `archived`

| Stage | Description |
|---|---|
| staging | Newly trained, not yet promoted |
| production | Currently serving live predictions |
| archived | Retired, kept for rollback |

```bash
# Register a new model version
python -c "from ingestion.model_registry import register_model; import os; print(register_model('prophet', '1.0', {}, os.getenv('AWS_BUCKET_NAME')))"

# Promote to production
python -c "from ingestion.model_registry import promote_model; import os; print(promote_model('model_id_here', os.getenv('AWS_BUCKET_NAME')))"
```

---

## 6. Model Serving (`ingestion/model_server.py`)

Loads the production model from the registry and generates live predictions.

```bash
python -c "from ingestion.model_server import serve_prediction; import os; print(serve_prediction('AAPL', os.getenv('AWS_BUCKET_NAME')))"
```

---

## 7. Model Explainability (`ingestion/model_explainer.py`)

Produces SHAP-approximated feature importances and human-readable explanations.

```bash
python -c "from ingestion.model_explainer import explain_prediction; import os; print(explain_prediction('AAPL', os.getenv('AWS_BUCKET_NAME')))"
```

---

## 8. Model Monitoring (`ingestion/model_monitor.py`)

Tracks prediction quality metrics daily and detects performance degradation.

| Metric | Description |
|---|---|
| MAE | Mean Absolute Error |
| RMSE | Root Mean Squared Error |
| MAPE | Mean Absolute Percentage Error |
| R2 | Coefficient of Determination |

| Severity | Trigger |
|---|---|
| none | RMSE within threshold |
| warning | RMSE increased 20–50% vs baseline |
| critical | RMSE increased > 50% vs baseline |

```bash
python -c "from ingestion.model_monitor import run_model_monitoring; import os; print(run_model_monitoring('AAPL', os.getenv('AWS_BUCKET_NAME')))"
```

---

## 9. Drift Detection (`ingestion/drift_detector.py`)

Uses Population Stability Index (PSI) to detect feature distribution shift.

| PSI Range | Severity |
|---|---|
| < 0.1 | None — stable |
| 0.1 – 0.2 | Moderate — monitor |
| > 0.2 | Significant — retrain |

```bash
python -c "from ingestion.drift_detector import run_drift_detection; import os; print(run_drift_detection('AAPL', os.getenv('AWS_BUCKET_NAME')))"
```

---

## 10. Retraining Triggers (`ingestion/retraining_trigger.py`)

Automates retraining based on drift signals and time-based schedule.

| Trigger Type | Condition |
|---|---|
| Drift-based | PSI > 0.2 on any feature |
| Schedule-based | Weekly (configurable) |
| Performance-based | RMSE degradation > 20% |

```bash
python -c "from ingestion.retraining_trigger import run_retraining_check; import os; print(run_retraining_check(['AAPL','MSFT','GOOGL','AMZN','TSLA'], os.getenv('AWS_BUCKET_NAME')))"
```

---

## 11. A/B Testing (`ingestion/ab_tester.py`)

Compares two model variants with hash-based consistent ticker assignment.

| Step | Command |
|---|---|
| Create experiment | `create_ab_experiment(name, model_a, model_b, split, bucket)` |
| Assign model | `assign_model(experiment_id, ticker, bucket)` |
| Record result | `record_ab_result(exp_id, model, ticker, pred, actual, bucket)` |
| Analyze | `analyze_ab_results(experiment_id, bucket)` |
| Conclude | `conclude_experiment(experiment_id, bucket)` |

Confidence levels: **low** (< 10 samples) · **medium** (< 30) · **high** (30+)

```bash
# Full A/B experiment lifecycle
python -c "from ingestion.ab_tester import create_ab_experiment; import os; print(create_ab_experiment('prophet_vs_ensemble', 'prophet', 'ensemble', 0.5, os.getenv('AWS_BUCKET_NAME')))"
```

---

## 14. Online Feature Engineering (`ingestion/online_feature_engineer.py`)
Module: online_feature_engineer.py
Features: rolling stats, microstructure, regime
Update: Real-time with every new price

---

## 15. Adaptive Modeling (`ingestion/adaptive_model.py`)
Module: adaptive_model.py
Selection: Regime-based model routing
Adaptation: Weight updates from accuracy feedback
Drift: Concept drift detection + retraining trigger

---

## Complete MLOps Lifecycle (15 stages)
1. Feature Engineering (batch)
2. AutoML (5 candidates)
3. Hyperparameter Tuning (GridSearchCV)
4. Model Registry (staging → production)
5. Experiment Tracking
6. Feature Store (S3)
7. Model Serving (endpoints)
8. Model Explainability (SHAP)
9. Drift Detection (PSI)
10. Retraining Triggers
11. Model Monitor (MAE/RMSE)
12. A/B Testing (hash-based)
13. Deployment Manager (3 envs)
14. Online Feature Engineering
15. Adaptive Modeling (regime-based)

---

## MLOps S3 Layout

```
s3://<bucket>/
├── features/
│   └── YYYY/MM/DD/
│       └── {TICKER}.json
├── models/
│   ├── registry/
│   │   └── {model_id}/
│   │       ├── metadata.json
│   │       └── artifacts/
│   ├── monitoring/
│   │   └── YYYY/MM/DD/
│   │       └── {TICKER}.json
│   └── experiments/
│       └── {experiment_id}/
│           ├── config.json
│           ├── conclusion.json
│           └── results/
│               └── {TICKER}_{timestamp}.json
```

---

## MLOps Maturity Level

| Capability | Status |
|---|---|
| Feature engineering | ✅ Implemented |
| Feature store | ✅ Implemented |
| Experiment tracking | ✅ Implemented |
| Model registry | ✅ Implemented |
| Model serving | ✅ Implemented |
| Model explainability | ✅ Implemented |
| Model monitoring | ✅ Implemented |
| Drift detection | ✅ Implemented |
| Retraining automation | ✅ Implemented |
| A/B testing | ✅ Implemented |
| Statistical significance | ⬜ Future improvement |
| Online learning | ⬜ Future improvement |

## MLOps Pipeline Complete! 🎉
All 15 MLOps stages implemented over 89 days:

| Stage | Module | Day Built |
|---|---|---|
| Feature Eng | feature_engineer.py | Day 32 |
| AutoML | automl_pipeline.py | Day 70 |
| Tuning | hyperparameter_tuner.py | Day 70 |
| Registry | model_registry.py | Day 28 |
| Experiments | experiment_tracker.py | Day 28 |
| Feature Store | feature_store.py | Day 41 |
| Serving | model_server.py | Day 41 |
| Explainability | model_explainer.py | Day 44 |
| Drift | drift_detector.py | Day 51 |
| Retraining | retraining_trigger.py | Day 51 |
| Monitor | model_monitor.py | Day 56 |
| A/B Testing | ab_tester.py | Day 56 |
| Deployment | model_deployment_manager.py | Day 83 |
| Online Feat | online_feature_engineer.py | Day 87 |
| Adaptive | adaptive_model.py | Day 87 |
