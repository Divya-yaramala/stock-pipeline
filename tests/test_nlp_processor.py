import pytest  # noqa: F401

from ingestion.nlp_processor import (
    calculate_text_sentiment,
    extract_financial_entities,
    summarize_text,
    tokenize_text,
)


def test_tokenize_text_removes_stopwords():
    tokens = tokenize_text("the stock is bullish")
    assert "the" not in tokens
    assert "is" not in tokens
    assert "bullish" in tokens


def test_extract_financial_entities_tickers():
    text = "AAPL and MSFT surged today"
    entities = extract_financial_entities(text)
    assert "AAPL" in entities["tickers"]
    assert "MSFT" in entities["tickers"]


def test_calculate_text_sentiment_positive():
    text = "The market is bullish with a rally and an upgrade expected"
    result = calculate_text_sentiment(text)
    assert result["label"] == "BULLISH"


def test_calculate_text_sentiment_negative():
    text = "Stocks are bearish with a plunge and a downgrade forecast"
    result = calculate_text_sentiment(text)
    assert result["label"] == "BEARISH"


def test_summarize_text_length():
    sentences = [
        "Sentence one about earnings.",
        "Sentence two about revenue.",
        "Sentence three about bullish rally.",
        "Sentence four about market.",
        "Sentence five about stocks.",
        "Sentence six about trading.",
        "Sentence seven about surge.",
        "Sentence eight about forecast.",
        "Sentence nine about guidance.",
        "Sentence ten about beat.",
    ]
    text = " ".join(sentences)
    summary = summarize_text(text, max_sentences=3)
    summary_sentences = [s for s in summary.split(". ") if s.strip()]
    assert len(summary_sentences) <= 3
