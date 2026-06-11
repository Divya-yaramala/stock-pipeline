import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from ingestion.model_comparator import (
    evaluate_model,
    prepare_training_data,
    train_linear_regression,
    train_random_forest,
)


def _sample_feature_df(n: int = 100) -> pd.DataFrame:
    np.random.seed(0)
    return pd.DataFrame(
        {
            "daily_return": np.random.uniform(-3, 3, n),
            "high_low_range": np.random.uniform(1, 10, n),
            "price_position": np.random.uniform(0, 1, n),
            "body_size": np.random.uniform(0.5, 5, n),
            "volume_ratio": np.random.uniform(0.5, 2.5, n),
            "roc_5": np.random.uniform(-5, 5, n),
            "roc_10": np.random.uniform(-8, 8, n),
        }
    )


def test_prepare_training_data_split():
    df = _sample_feature_df(100)
    X_train, X_test, y_train, y_test = prepare_training_data(df, test_size=0.2)
    assert len(X_train) == 80
    assert len(X_test) == 20
    assert len(y_train) == 80
    assert len(y_test) == 20


def test_train_random_forest_returns_dict():
    df = _sample_feature_df(50)
    X_train, X_test, y_train, y_test = prepare_training_data(df, test_size=0.2)
    result = train_random_forest(X_train, y_train)
    assert "model" in result
    assert "feature_importances" in result
    assert isinstance(result["feature_importances"], dict)


def test_train_linear_regression_returns_dict():
    df = _sample_feature_df(50)
    X_train, X_test, y_train, y_test = prepare_training_data(df, test_size=0.2)
    result = train_linear_regression(X_train, y_train)
    assert "model" in result
    assert "coefficients" in result
    assert isinstance(result["coefficients"], dict)


def test_evaluate_model_metrics():
    df = _sample_feature_df(50)
    X_train, X_test, y_train, y_test = prepare_training_data(df, test_size=0.2)
    rf = train_random_forest(X_train, y_train)
    metrics = evaluate_model(rf["model"], X_test, y_test, "RandomForest")
    for key in ["model_name", "MAE", "RMSE", "R2"]:
        assert key in metrics, f"Missing metric: {key}"
    assert metrics["model_name"] == "RandomForest"
    assert metrics["MAE"] >= 0
    assert metrics["RMSE"] >= 0


def test_compare_models_has_winner():
    df = _sample_feature_df(100)
    records = df.astype(str).to_dict(orient="records")
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(records).encode())}
    mock_s3.put_object.return_value = {}

    with patch("ingestion.model_comparator.boto3.client", return_value=mock_s3):
        from ingestion.model_comparator import compare_models

        result = compare_models("AAPL", "test-bucket")

    assert "winner" in result
    assert result["winner"] in ("RandomForest", "LinearRegression")
    assert "models" in result
