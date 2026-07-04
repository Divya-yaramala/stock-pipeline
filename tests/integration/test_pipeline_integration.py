import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pandas as pd


class TestPipelineIntegration:
    def test_fetch_to_validate_flow(self):
        mock_df = pd.DataFrame(
            {
                "Open": [150.0],
                "High": [155.0],
                "Low": [149.0],
                "Close": [153.0],
                "Volume": [1_000_000],
            },
            index=pd.to_datetime(["2026-07-03"]),
        )
        with patch("ingestion.fetch_stocks.yf.download", return_value=mock_df):
            from ingestion.fetch_stocks import fetch_stock_data

            result_df = fetch_stock_data("AAPL")

        from ingestion.data_validator import validate_stock_data

        result_df.columns = [c.lower() for c in result_df.columns]
        report = validate_stock_data(result_df, "AAPL")

        assert report["passed"] is True

    def test_validate_to_anomaly_flow(self):
        data = {
            "open": [150.0, 151.0, 149.0, 152.0, 148.0, 153.0, 147.0, 154.0, 146.0, 155.0],
            "high": [155.0, 156.0, 154.0, 157.0, 153.0, 158.0, 152.0, 159.0, 151.0, 160.0],
            "low": [148.0, 149.0, 147.0, 150.0, 146.0, 151.0, 145.0, 152.0, 144.0, 153.0],
            "close": [152.0, 153.0, 150.0, 154.0, 149.0, 155.0, 148.0, 156.0, 147.0, 157.0],
            "volume": [
                1000000,
                1100000,
                900000,
                1200000,
                800000,
                1300000,
                700000,
                1400000,
                600000,
                1500000,
            ],
        }
        df = pd.DataFrame(data)

        from ingestion.anomaly_detector import detect_anomalies

        result_df = detect_anomalies(df, "AAPL")
        result = result_df.to_dict("records")[0]

        assert "is_anomaly" in result

    def test_sentiment_to_s3_flow(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "articles": [
                {"title": "Apple reports record profit growth"},
                {"title": "Tesla faces sales decline risk"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("ingestion.news_sentiment.requests.get", return_value=mock_response):
            with patch("ingestion.news_sentiment.boto3") as mock_boto3:
                mock_s3 = MagicMock()
                mock_boto3.client.return_value = mock_s3
                with patch.dict(
                    os.environ,
                    {"NEWS_API_KEY": "test-key", "AWS_BUCKET_NAME": "test-bucket"},
                ):
                    from ingestion.news_sentiment import run_sentiment_analysis

                    run_sentiment_analysis()

        assert mock_s3.put_object.call_count >= 1

    def test_cache_integration(self):
        mock_data: Dict[str, Any] = {"price": 150.0, "ticker": "AAPL"}
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        cache_entry = {
            "data": mock_data,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": 300,
            "expires_at": future_time,
        }

        with patch("ingestion.cache_manager.boto3") as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.client.return_value = mock_s3
            mock_s3.get_object.return_value = {
                "Body": MagicMock(read=MagicMock(return_value=json.dumps(cache_entry).encode()))
            }

            from ingestion.cache_manager import get_from_cache, save_to_cache

            save_to_cache("test_key", mock_data, "test-bucket", ttl_seconds=300)
            result = get_from_cache("test_key", "test-bucket")

        assert result is not None
        assert float(str(result["price"])) == float(str(mock_data["price"]))

    def test_portfolio_to_snapshot_flow(self):
        portfolio: Dict[str, Any] = {"AAPL": 10, "MSFT": 5, "GOOGL": 3}
        prices: Dict[str, Any] = {"AAPL": 150.0, "MSFT": 300.0, "GOOGL": 100.0}

        from ingestion.portfolio_tracker import calculate_portfolio_value, save_portfolio_snapshot

        result = calculate_portfolio_value(portfolio, prices)
        assert "total_value" in result

        with patch("ingestion.portfolio_tracker.boto3") as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.client.return_value = mock_s3
            saved = save_portfolio_snapshot(result, "test-bucket", "2026-07-03")

        assert saved is True
