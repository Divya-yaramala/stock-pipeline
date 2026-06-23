from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from ingestion.model_explainer import (
    calculate_feature_importance,
    generate_explanation_report,
    save_explanation_to_s3,
)

_FEATURES = ["roc_5", "volume_ratio", "daily_return", "high_low_range", "body_size"]


def _trained_rf():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.random((40, len(_FEATURES))), columns=_FEATURES)
    y = rng.random(40)
    model = RandomForestRegressor(n_estimators=10, random_state=0)
    model.fit(X, y)
    return model, X


def test_calculate_feature_importance_sorted():
    model, X = _trained_rf()
    result = calculate_feature_importance(model, X.columns.tolist())
    values = list(result.values())
    assert values == sorted(values, reverse=True)


def test_generate_explanation_report_structure():
    model, X = _trained_rf()
    report = generate_explanation_report("AAPL", model, X, prediction=150.25)
    assert "explanation" in report
    assert "top_features" in report
    assert "prediction" in report


def test_save_explanation_to_s3_success():
    mock_s3 = MagicMock()
    explanation = {"ticker": "AAPL", "explanation": "test", "prediction": 150.0}
    with patch("ingestion.model_explainer.boto3.client", return_value=mock_s3):
        result = save_explanation_to_s3(explanation, "AAPL", "test-bucket", "2026-06-23")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_calculate_feature_importance_keys():
    model, X = _trained_rf()
    result = calculate_feature_importance(model, X.columns.tolist())
    for feat in _FEATURES:
        assert feat in result


def test_generate_explanation_has_ticker():
    model, X = _trained_rf()
    report = generate_explanation_report("TSLA", model, X, prediction=250.0)
    assert "TSLA" in report["explanation"]
    assert report["ticker"] == "TSLA"
