from unittest.mock import MagicMock, patch

import numpy as np
from sklearn.linear_model import LinearRegression

from ingestion.hyperparameter_tuner import (
    cross_validate_model,
    save_tuning_results,
    tune_random_forest,
)


def _make_data(n: int = 60):
    rng = np.random.default_rng(0)
    X = rng.random((n, 4))
    y = rng.random(n)
    return X, y


def test_cross_validate_model_structure():
    X, y = _make_data()
    model = LinearRegression()
    result = cross_validate_model(model, X, y, cv_folds=3)
    assert isinstance(result, dict)
    assert "mean_score" in result
    assert "std_score" in result
    assert "scores" in result


def test_cross_validate_model_scores_list():
    X, y = _make_data()
    model = LinearRegression()
    cv_folds = 4
    result = cross_validate_model(model, X, y, cv_folds=cv_folds)
    assert isinstance(result["scores"], list)
    assert len(result["scores"]) == cv_folds


def test_tune_random_forest_returns_best_params():
    X, y = _make_data(50)
    result = tune_random_forest(X, y, cv_folds=2)
    assert isinstance(result, dict)
    assert "best_params" in result
    assert isinstance(result["best_params"], dict)


def test_save_tuning_results_success():
    results = {
        "best_params": {"n_estimators": 100, "max_depth": 5, "min_samples_split": 2},
        "best_score": -0.05,
        "cv_results": {},
    }
    with patch("ingestion.hyperparameter_tuner.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        ok = save_tuning_results("AAPL", results, "test-bucket", "2026-07-19")
    assert ok is True
    mock_s3.put_object.assert_called_once()


def test_tune_random_forest_best_score_negative():
    X, y = _make_data(50)
    result = tune_random_forest(X, y, cv_folds=2)
    assert isinstance(result["best_score"], float)
