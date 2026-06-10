import json
from unittest.mock import MagicMock, patch

from ingestion.news_sentiment import analyze_sentiment, fetch_news_headlines, save_sentiment_to_s3


def test_analyze_sentiment_bullish():
    headlines = [
        "Apple reports record profit and strong growth",
        "AAPL stock surges after earnings beat",
        "Analysts upgrade Apple with buy rating",
    ]
    result = analyze_sentiment(headlines)
    assert result["sentiment_label"] == "BULLISH"
    assert result["positive_count"] > result["negative_count"]
    assert result["sentiment_score"] > 20


def test_analyze_sentiment_bearish():
    headlines = [
        "Apple reports major loss as revenue declines",
        "AAPL misses earnings, analysts downgrade to sell",
        "Apple faces risk of falling market share",
    ]
    result = analyze_sentiment(headlines)
    assert result["sentiment_label"] == "BEARISH"
    assert result["negative_count"] > result["positive_count"]
    assert result["sentiment_score"] < -20


def test_analyze_sentiment_neutral():
    headlines = [
        "Apple releases new product update",
        "AAPL shares trade flat in morning session",
    ]
    result = analyze_sentiment(headlines)
    assert result["sentiment_label"] == "NEUTRAL"
    assert -20 <= result["sentiment_score"] <= 20
    assert "positive_count" in result
    assert "negative_count" in result
    assert "neutral_count" in result


def test_save_sentiment_to_s3():
    mock_s3 = MagicMock()
    with patch("ingestion.news_sentiment.boto3.client", return_value=mock_s3):
        sentiment = {
            "positive_count": 3,
            "negative_count": 1,
            "neutral_count": 1,
            "sentiment_score": 40.0,
            "sentiment_label": "BULLISH",
        }
        result = save_sentiment_to_s3(sentiment, "AAPL", "test-bucket", "2026-06-07")

    assert result is True
    mock_s3.put_object.assert_called_once()
    call_kwargs = mock_s3.put_object.call_args.kwargs
    assert call_kwargs["Bucket"] == "test-bucket"
    assert "processed/sentiment/2026/06/07/AAPL.json" == call_kwargs["Key"]
    saved = json.loads(call_kwargs["Body"].decode("utf-8"))
    assert saved["ticker"] == "AAPL"
    assert saved["sentiment_label"] == "BULLISH"


def test_fetch_news_headlines_rss_fallback():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = (
        "<?xml version='1.0'?>\n"
        "<rss><channel>\n"
        "<title>Yahoo Finance</title>\n"
        "<item><title>AAPL stock surges on strong earnings</title></item>\n"
        "<item><title>Apple beats revenue expectations</title></item>\n"
        "</channel></rss>"
    )
    mock_response.raise_for_status = MagicMock()

    with patch.dict("os.environ", {"NEWS_API_KEY": ""}, clear=False):
        with patch("ingestion.news_sentiment.requests.get", return_value=mock_response):
            headlines = fetch_news_headlines("AAPL", "Apple")

    assert isinstance(headlines, list)
