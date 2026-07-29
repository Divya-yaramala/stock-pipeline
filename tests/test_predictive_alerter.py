from unittest.mock import MagicMock, patch

from ingestion.predictive_alerter import (
    generate_predictive_alerts,
    predict_anomaly_probability,
    predict_quality_degradation,
    predict_sla_risk,
)


def test_predict_anomaly_probability_range():
    prices = [100.0, 101.0, 100.5, 100.8, 99.9, 100.2, 100.4, 100.1, 100.6, 115.0]
    result = predict_anomaly_probability(prices, window=9)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0


def test_predict_quality_degradation_degrading():
    scores = [95.0, 93.0, 91.0, 89.0, 87.0, 85.0, 83.0]
    result = predict_quality_degradation(scores, threshold=80.0)
    assert result["degrading"] is True


def test_predict_quality_degradation_stable():
    scores = [92.0, 91.5, 92.3, 91.8, 92.1, 91.9, 92.0]
    result = predict_quality_degradation(scores, threshold=80.0)
    assert result["degrading"] is False


def test_predict_sla_risk_at_risk():
    times = [5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]
    result = predict_sla_risk(times, sla_target_hour=7)
    assert result["at_risk"] is True


def test_generate_predictive_alerts_returns_list():
    metrics = {
        "recent_prices": [100.0, 101.0, 100.5, 100.8, 99.9, 100.2, 100.4, 100.1, 100.6, 130.0],
        "quality_scores": [],
        "completion_times": [],
    }
    with patch("ingestion.predictive_alerter.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        result = generate_predictive_alerts("AAPL", metrics, "test-bucket")
    assert isinstance(result, list)
