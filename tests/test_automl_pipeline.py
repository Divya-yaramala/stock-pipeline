from unittest.mock import MagicMock, patch

import numpy as np

from ingestion.automl_pipeline import (
    evaluate_candidate,
    run_automl,
    save_automl_results,
    train_candidate,
)


def _make_data(n: int = 100):
    rng = np.random.default_rng(42)
    X = rng.random((n, 5))
    y = rng.random(n)
    return X, y


def test_train_candidate_random_forest():
    X, y = _make_data()
    cfg = {"name": "random_forest", "params": {"n_estimators": 10, "max_depth": 3}}
    result = train_candidate(cfg, X, y)
    assert isinstance(result, dict)
    assert "model" in result
    assert result["name"] == "random_forest"
    assert result["train_time_seconds"] >= 0.0


def test_evaluate_candidate_structure():
    X, y = _make_data()
    cfg = {"name": "linear_regression", "params": {}}
    candidate = train_candidate(cfg, X, y)
    X_test, y_test = _make_data(20)
    metrics = evaluate_candidate(candidate, X_test, y_test)
    assert isinstance(metrics, dict)
    assert "mae" in metrics
    assert "rmse" in metrics
    assert "r2" in metrics


def test_run_automl_returns_winner():
    X_train, y_train = _make_data(80)
    X_test, y_test = _make_data(20)
    result = run_automl(X_train, y_train, X_test, y_test)
    assert isinstance(result, dict)
    assert "winner" in result
    assert isinstance(result["winner"], str)
    assert "results" in result
    assert "best_metrics" in result


def test_save_automl_results_success():
    results = {
        "winner": "random_forest",
        "results": [],
        "best_metrics": {"name": "random_forest", "mae": 0.1, "rmse": 0.2, "r2": 0.8},
    }
    with patch("ingestion.automl_pipeline.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        ok = save_automl_results("AAPL", results, "test-bucket", "2026-07-19")
    assert ok is True
    mock_s3.put_object.assert_called_once()


def test_run_automl_winner_has_lowest_rmse():
    X_train, y_train = _make_data(80)
    X_test, y_test = _make_data(20)
    result = run_automl(X_train, y_train, X_test, y_test)
    winner_name = result["winner"]
    winner_rmse = result["best_metrics"]["rmse"]
    for r in result["results"]:
        assert (
            winner_rmse <= r["rmse"] + 1e-9
        ), f"Winner {winner_name} RMSE {winner_rmse} > {r['name']} RMSE {r['rmse']}"
