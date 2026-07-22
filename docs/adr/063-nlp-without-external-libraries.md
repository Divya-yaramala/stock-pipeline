# ADR 063 - NLP Without External Libraries

## Status

Accepted

## Context

Needed NLP capabilities without heavy dependencies (NLTK, spaCy, transformers) to keep the
pipeline lean and CI/CD fast.

## Decision

Built custom NLP processor using pure Python regex and string operations.

## Reasons

- No additional dependencies (no NLTK download, no spaCy models)
- Financial domain knowledge encoded in FINANCIAL_TERMS dict
- Regex-based entity extraction sufficient for structured financial text
- TF-IDF implemented from scratch (only needs math module)
- CI/CD stays fast (no large model downloads)

## Consequences

- Less accurate than transformer models (BERT, FinBERT)
- Cannot understand context or sarcasm
- Future: add FinBERT for production-grade NLP
