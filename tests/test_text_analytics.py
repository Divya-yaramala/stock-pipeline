import pytest  # noqa: F401

from ingestion.text_analytics import (
    calculate_tfidf,
    classify_news_category,
    extract_price_targets,
    find_key_phrases,
)


def test_calculate_tfidf_structure():
    documents = [
        "Apple reported strong earnings this quarter",
        "Microsoft revenue beat analyst expectations",
        "Google stock surged after profit announcement",
    ]
    result = calculate_tfidf(documents)
    assert isinstance(result, dict)
    assert "0" in result
    assert "1" in result
    assert "2" in result


def test_classify_news_earnings():
    text = "The company reported earnings with strong revenue and profit growth"
    category = classify_news_category(text)
    assert category == "earnings"


def test_classify_news_merger():
    text = "The acquisition merger deal was announced today"
    category = classify_news_category(text)
    assert category == "merger"


def test_extract_price_targets_found():
    text = "Goldman Sachs set a price target of $200 for the stock"
    targets = extract_price_targets(text)
    assert len(targets) > 0
    assert targets[0]["price"] == 200.0


def test_find_key_phrases_returns_list():
    text = "Apple Stock Market Rally shows Strong Growth in Technology Sector"
    phrases = find_key_phrases(text)
    assert isinstance(phrases, list)
    assert all(isinstance(p, str) for p in phrases)
