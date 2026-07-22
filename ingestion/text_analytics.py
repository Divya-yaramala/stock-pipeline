import datetime
import json
import logging
import math
import os  # noqa: F401
import re
from typing import Any, Dict, List, Optional  # noqa: F401

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_tfidf(documents: List[str]) -> Dict[str, Dict[str, float]]:
    total_docs = len(documents)
    tokenized: List[List[str]] = []
    for doc in documents:
        tokens = re.sub(r"[^\w\s]", "", doc.lower()).split()
        tokenized.append(tokens)

    doc_freq: Dict[str, int] = {}
    for tokens in tokenized:
        for term in set(tokens):
            doc_freq[term] = doc_freq.get(term, 0) + 1

    result: Dict[str, Dict[str, float]] = {}
    for idx, tokens in enumerate(tokenized):
        total_terms = len(tokens) if tokens else 1
        term_counts: Dict[str, int] = {}
        for term in tokens:
            term_counts[term] = term_counts.get(term, 0) + 1
        tfidf_scores: Dict[str, float] = {}
        for term, count in term_counts.items():
            tf = float(count) / float(total_terms)
            idf = math.log(float(total_docs) / float(doc_freq.get(term, 1)))
            tfidf_scores[term] = tf * idf
        result[str(idx)] = tfidf_scores

    logger.info("TF-IDF calculated for %d documents", total_docs)
    return result


def find_key_phrases(text: str, top_n: int = 5) -> List[str]:
    pattern = r"\b(?:[A-Z][a-z]+\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b"
    phrases = re.findall(pattern, text)
    phrase_counts: Dict[str, int] = {}
    for phrase in phrases:
        phrase = phrase.strip()
        if len(phrase) > 3:
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
    sorted_phrases = sorted(phrase_counts.items(), key=lambda x: x[1], reverse=True)
    top_phrases = [p for p, _ in sorted_phrases[:top_n]]
    logger.info("Key phrases found: %d", len(top_phrases))
    return top_phrases


def classify_news_category(text: str) -> str:
    text_lower = text.lower()
    categories = {
        "earnings": ["earnings", "revenue", "profit", "eps"],
        "merger": ["acquisition", "merger", "buyout", "deal"],
        "product": ["launch", "product", "release", "announce"],
        "regulatory": ["sec", "fda", "regulation", "fine"],
        "analyst": ["upgrade", "downgrade", "price target"],
        "macro": ["fed", "inflation", "interest rate", "gdp"],
    }
    scores: Dict[str, int] = {}
    for category, keywords in categories.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score

    if not scores:
        result = "general"
    else:
        result = max(scores, key=lambda k: scores[k])

    logger.info("News classified as: %s", result)
    return result


def extract_price_targets(text: str) -> List[Dict[str, Any]]:
    patterns = [
        r"price target (?:of )?\$(\d+(?:\.\d+)?)",
        r"target price \$(\d+(?:\.\d+)?)",
        r"price target (?:to )?\$(\d+(?:\.\d+)?)",
        r"raised (?:its )?(?:price )?target (?:to )?\$(\d+(?:\.\d+)?)",
    ]
    targets: List[Dict[str, Any]] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            price = float(str(match.group(1)))
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            context = text[start:end].strip()
            targets.append({"price": price, "context": context})

    logger.info("Price targets found: %d", len(targets))
    return targets


def run_text_analytics(ticker: str, news_texts: List[str], bucket: str) -> Dict[str, Any]:
    tfidf = calculate_tfidf(news_texts)
    categories: List[str] = [classify_news_category(t) for t in news_texts]
    all_targets: List[Dict[str, Any]] = []
    all_phrases: List[str] = []
    for text in news_texts:
        all_targets.extend(extract_price_targets(text))
        all_phrases.extend(find_key_phrases(text))

    result: Dict[str, Any] = {
        "ticker": ticker,
        "text_count": len(news_texts),
        "tfidf_keys": list(tfidf.keys()),
        "categories": categories,
        "price_targets": all_targets,
        "key_phrases": list(set(all_phrases))[:20],
        "analyzed_at": datetime.datetime.utcnow().isoformat(),
    }

    now = datetime.datetime.utcnow()
    s3_key = "processed/text_analytics/{}/{}/{}/{}.json".format(
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
        logger.info("Saved text analytics to s3://%s/%s", bucket, s3_key)
    except Exception as e:
        logger.warning("S3 upload skipped: %s", str(e))

    logger.info("Text Analytics Complete for %s", ticker)
    return result


if __name__ == "__main__":
    pass
