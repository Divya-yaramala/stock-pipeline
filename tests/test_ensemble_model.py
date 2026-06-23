from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from ingestion.ensemble_model import (
    ensemble_predict,
    evaluate_ensemble,
    run_ensemble_prediction,
    train_ensemble,
)

_FEATURES = ["high_low_range", "body_size", "volume_ratio", "roc_5", "roc_10"]


def _make_data(n: int = 50):
    rng = np.random.default_rng(42)
    X = pd.DataFrame(rng.random((n, len(_FEATURES))), columns=_FEATURES)
    y = pd.Series(rng.random(n))
    return X, y


def test_train_ensemble_returns_three_models():
    X, y = _make_data()
    models = train_ensemble(X, y)
    assert len(models) == 3
    assert "random_forest" in models
    assert "gradient_boosting" in models
    assert "linear_regression" in models


def test_ensemble_predict_shape():
    X_train, y_train = _make_data(50)
    X_test, _ = _make_data(10)
    models = train_ensemble(X_train, y_train)
    preds = ensemble_predict(models, X_test)
    assert preds.shape == (10,)


def test_ensemble_predict_weighted():
    X_train, y_train = _make_data(50)
    X_test, _ = _make_data(10)
    models = train_ensemble(X_train, y_train)
    preds_equal = ensemble_predict(models, X_test)
    preds_weighted = ensemble_predict(models, X_test, weights=[0.5, 0.3, 0.2])
    assert preds_weighted.shape == (10,)
    assert not np.allclose(preds_equal, preds_weighted)


def test_evaluate_ensemble_metrics():
    y_true = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    y_pred = np.array([1.1, 1.9, 3.1, 3.9, 5.1])
    metrics = evaluate_ensemble(y_pred, y_true)
    assert "MAE" in metrics
    assert "RMSE" in metrics
    assert "R2" in metrics
    assert metrics["MAE"] >= 0
    assert metrics["RMSE"] >= 0


def test_run_ensemble_prediction_structure():
    n = 30
    rng = np.random.default_rng(0)
    records = [
        {
            "daily_return": float(rng.random()),
            "high_low_range": float(rng.random()),
            "price_position": float(rng.random()),
            "body_size": float(rng.random()),
            "volume_ratio": float(rng.random()),
            "roc_5": float(rng.random()),
            "roc_10": float(rng.random()),
        }
        for _ in range(n)
    ]
    import json
    from io import BytesIO

    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(records).encode("utf-8"))}
    with patch("ingestion.ensemble_model.boto3.client", return_value=mock_s3):
        result = run_ensemble_prediction("AAPL", "test-bucket")
    assert "results" in result
    assert result["ticker"] == "AAPL"
