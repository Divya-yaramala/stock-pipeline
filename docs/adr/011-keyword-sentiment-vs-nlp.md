# ADR 011 - Keyword Sentiment vs NLP Models

## Status

Accepted

## Context

The pipeline needed sentiment analysis for stock news headlines to classify market mood as BULLISH, BEARISH, or NEUTRAL. The standard Python NLP libraries — NLTK/VADER, spaCy, and transformer-based models like FinBERT — provide more sophisticated text understanding but come with significant dependency and runtime overhead.

## Decision

Implement a keyword-based sentiment scorer in `ingestion/news_sentiment.py` using hand-curated finance-specific positive and negative word lists, rather than adding NLTK, VADER, or any transformer model as a dependency.

## Reasons

- **No ML model dependencies to manage**: NLTK requires corpus downloads; transformers require model files (hundreds of MB); keyword matching requires only Python built-ins.
- **Fast execution — no model loading time**: Transformer models take seconds to load into memory on each pipeline run. Keyword matching is instantaneous.
- **Finance-specific keywords more accurate than general NLP**: General sentiment models are trained on movie reviews and social media. A curated list of finance terms (beat, miss, upgrade, downgrade) maps directly to market-relevant signals.
- **No GPU required**: Transformer inference benefits from GPU; our pipeline runs on standard CPU instances.
- **Easy to update keyword lists**: Adding a new signal word takes one line of code with no retraining or model versioning required.

## Consequences

- **Less accurate than transformer models (BERT, FinBERT)**: Keyword matching cannot weigh context — "not a loss" would still trigger on "loss".
- **Cannot understand context or sarcasm**: A headline like "Apple's 'record' loss surprises analysts" would score incorrectly.
- **Future improvement: replace with FinBERT for production**: HuggingFace's `ProsusAI/finbert` is specifically trained on financial news and would be the natural upgrade path when accuracy becomes a priority.
