import json
import logging
import os
from datetime import datetime

import boto3
import requests

logger = logging.getLogger(__name__)

TICKERS = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Google",
    "AMZN": "Amazon",
    "TSLA": "Tesla",
}

POSITIVE_KEYWORDS = ["growth", "profit", "beat", "surge", "record", "upgrade", "buy"]
NEGATIVE_KEYWORDS = ["loss", "decline", "miss", "fall", "downgrade", "sell", "risk"]


def fetch_news_headlines(ticker: str, company_name: str) -> list:
    api_key = os.getenv("NEWS_API_KEY", "")
    if api_key:
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": company_name,
                "apiKey": api_key,
                "pageSize": 20,
                "language": "en",
                "sortBy": "publishedAt",
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            articles = response.json().get("articles", [])
            return [a.get("title", "") for a in articles if a.get("title")]
        except Exception as e:
            logger.warning("NewsAPI failed for %s: %s — falling back to Yahoo RSS", ticker, e)

    try:
        rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}"
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()
        headlines = []
        for line in response.text.splitlines():
            line = line.strip()
            if line.startswith("<title>") and line.endswith("</title>"):
                title = line[7:-8].strip()
                if title and title != company_name:
                    headlines.append(title)
        return headlines
    except Exception as e:
        logger.error("Yahoo RSS fallback failed for %s: %s", ticker, e)
        return []


def analyze_sentiment(headlines: list) -> dict:
    positive_count = 0
    negative_count = 0
    neutral_count = 0

    for headline in headlines:
        lower = headline.lower()
        pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in lower)
        neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in lower)
        if pos > neg:
            positive_count += 1
        elif neg > pos:
            negative_count += 1
        else:
            neutral_count += 1

    total = len(headlines) if headlines else 1
    sentiment_score = ((positive_count - negative_count) / total) * 100

    if sentiment_score > 20:
        sentiment_label = "BULLISH"
    elif sentiment_score < -20:
        sentiment_label = "BEARISH"
    else:
        sentiment_label = "NEUTRAL"

    return {
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "sentiment_score": round(sentiment_score, 2),
        "sentiment_label": sentiment_label,
    }


def save_sentiment_to_s3(sentiment: dict, ticker: str, bucket: str, date: str) -> bool:
    try:
        s3 = boto3.client("s3")
        path_date = date.replace("-", "/")
        key = f"processed/sentiment/{path_date}/{ticker}.json"
        body = json.dumps({**sentiment, "ticker": ticker, "date": date}, indent=2)
        s3.put_object(Bucket=bucket, Key=key, Body=body.encode("utf-8"), ContentType="application/json")
        logger.info("Saved sentiment for %s to s3://%s/%s", ticker, bucket, key)
        return True
    except Exception as e:
        logger.error("Failed to save sentiment for %s: %s", ticker, e)
        return False


def run_sentiment_analysis() -> dict:
    bucket = os.getenv("AWS_BUCKET_NAME", "")
    date = datetime.utcnow().strftime("%Y-%m-%d")
    results = {}
    bullish, bearish, neutral = 0, 0, 0

    for ticker, company in TICKERS.items():
        headlines = fetch_news_headlines(ticker, company)
        sentiment = analyze_sentiment(headlines)
        sentiment["headline_count"] = len(headlines)
        results[ticker] = sentiment

        label = sentiment["sentiment_label"]
        if label == "BULLISH":
            bullish += 1
        elif label == "BEARISH":
            bearish += 1
        else:
            neutral += 1

        if bucket:
            save_sentiment_to_s3(sentiment, ticker, bucket, date)

    logger.info("Sentiment analysis complete: %d BULLISH, %d BEARISH, %d NEUTRAL", bullish, bearish, neutral)
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_sentiment_analysis()
