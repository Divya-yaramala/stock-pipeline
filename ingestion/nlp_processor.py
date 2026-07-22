import collections  # noqa: F401
import datetime
import json
import logging
import os  # noqa: F401
import re
from collections import Counter  # noqa: F401
from typing import Any, Dict, List, Optional  # noqa: F401

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FINANCIAL_TERMS: Dict[str, str] = {
    "bullish": "positive",
    "bearish": "negative",
    "rally": "positive",
    "selloff": "negative",
    "surge": "positive",
    "plunge": "negative",
    "outperform": "positive",
    "underperform": "negative",
    "upgrade": "positive",
    "downgrade": "negative",
    "beat": "positive",
    "miss": "negative",
    "guidance": "neutral",
    "forecast": "neutral",
    "earnings": "neutral",
}

STOP_WORDS = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at"}


def tokenize_text(text: str) -> List[str]:
    text_lower = text.lower()
    text_clean = re.sub(r"[^\w\s]", "", text_lower)
    tokens = [t for t in text_clean.split() if t not in STOP_WORDS]
    logger.info("Tokenized %d tokens", len(tokens))
    return tokens


def extract_financial_entities(text: str) -> Dict[str, List[str]]:
    tickers = re.findall(r"\b[A-Z]{2,5}\b", text)
    amounts = re.findall(r"\$\d+(?:,\d{3})*(?:\.\d+)?", text)
    percentages = re.findall(r"\d+(?:\.\d+)?%", text)
    text_lower = text.lower()
    terms = [term for term in FINANCIAL_TERMS if term in text_lower]
    result: Dict[str, List[str]] = {
        "tickers": tickers,
        "amounts": amounts,
        "percentages": percentages,
        "terms": terms,
    }
    logger.info(
        "Entities found: %d tickers, %d amounts, %d percentages, %d terms",
        len(tickers),
        len(amounts),
        len(percentages),
        len(terms),
    )
    return result


def calculate_text_sentiment(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    positive_terms: List[str] = []
    negative_terms: List[str] = []
    neutral_count = 0

    for term, sentiment in FINANCIAL_TERMS.items():
        if term in text_lower:
            if sentiment == "positive":
                positive_terms.append(term)
            elif sentiment == "negative":
                negative_terms.append(term)
            else:
                neutral_count += 1

    total = len(positive_terms) + len(negative_terms) + neutral_count
    if total == 0:
        score = 0.0
    else:
        score = float(len(positive_terms) - len(negative_terms)) / float(total)

    if score > 0.1:
        label = "BULLISH"
    elif score < -0.1:
        label = "BEARISH"
    else:
        label = "NEUTRAL"

    result: Dict[str, Any] = {
        "score": score,
        "label": label,
        "positive_terms": positive_terms,
        "negative_terms": negative_terms,
    }
    logger.info("Sentiment: %s (score=%.2f)", label, score)
    return result


def summarize_text(text: str, max_sentences: int = 3) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    scored: List[tuple] = []
    for sentence in sentences:
        sentence_lower = sentence.lower()
        score = sum(1 for term in FINANCIAL_TERMS if term in sentence_lower)
        scored.append((score, sentence))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for _, s in scored[:max_sentences]]
    summary = " ".join(top)
    logger.info("Summary length: %d characters", len(summary))
    return summary


def analyze_earnings_report(report_text: str, ticker: str) -> Dict[str, Any]:
    entities = extract_financial_entities(report_text)
    sentiment = calculate_text_sentiment(report_text)
    summary = summarize_text(report_text)
    result: Dict[str, Any] = {
        "ticker": ticker,
        "entities": entities,
        "sentiment": sentiment,
        "summary": summary,
        "analyzed_at": datetime.datetime.utcnow().isoformat(),
    }
    logger.info("Analysis complete for %s", ticker)
    return result


def run_nlp_analysis(ticker: str, texts: List[str], bucket: str) -> Dict[str, Any]:
    combined_entities: Dict[str, List[str]] = {
        "tickers": [],
        "amounts": [],
        "percentages": [],
        "terms": [],
    }
    sentiments: List[Dict[str, Any]] = []

    for text in texts:
        entities = extract_financial_entities(text)
        for key in combined_entities:
            combined_entities[key].extend(entities[key])
        sentiments.append(calculate_text_sentiment(text))

    avg_score = (
        float(sum(float(str(s["score"])) for s in sentiments)) / float(len(sentiments))
        if sentiments
        else 0.0
    )

    result: Dict[str, Any] = {
        "ticker": ticker,
        "text_count": len(texts),
        "entities": combined_entities,
        "average_sentiment_score": avg_score,
        "analyzed_at": datetime.datetime.utcnow().isoformat(),
    }

    now = datetime.datetime.utcnow()
    s3_key = "processed/nlp/{}/{}/{}/{}.json".format(
        now.strftime("%Y"),
        now.strftime("%m"),
        now.strftime("%d"),
        ticker,
    )

    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=json.dumps(result),
            ContentType="application/json",
        )
        logger.info("Saved NLP analysis to s3://%s/%s", bucket, s3_key)
    except Exception as e:
        logger.warning("S3 upload skipped: %s", str(e))

    logger.info("NLP Analysis Complete for %s", ticker)
    return result


if __name__ == "__main__":
    pass
