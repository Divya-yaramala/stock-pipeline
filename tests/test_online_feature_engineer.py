from unittest.mock import MagicMock, patch

from ingestion.online_feature_engineer import (
    build_online_feature_vector,
    compute_regime_features,
    compute_rolling_features,
    save_online_features,
)


def test_compute_rolling_features_structure():
    prices = [float(100 + i) for i in range(20)]
    volumes = [float(1000000 + i * 10000) for i in range(20)]
    result = compute_rolling_features(prices, volumes)
    assert "price_mean" in result
    assert "volume_ratio" in result


def test_compute_rolling_features_momentum():
    prices = [float(100 + i * 2) for i in range(20)]
    volumes = [float(1000000) for _ in range(20)]
    result = compute_rolling_features(prices, volumes)
    assert result["price_momentum"] > 0


def test_compute_regime_features_trending():
    prices = [float(100 + i * 1.5) for i in range(30)]
    result = compute_regime_features(prices)
    assert result["regime"] == "trending"


def test_build_online_feature_vector_structure():
    prices = [float(150 + i * 0.1) for i in range(20)]
    volumes = [float(500000 + i * 5000) for i in range(20)]
    result = build_online_feature_vector("AAPL", prices, volumes)
    assert "ticker" in result
    assert "features" in result


def test_save_online_features_success():
    feature_vector = {"ticker": "AAPL", "features": {}, "regime": "trending"}
    with patch("ingestion.online_feature_engineer.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        result = save_online_features("AAPL", feature_vector, "test-bucket")
    assert result is True
