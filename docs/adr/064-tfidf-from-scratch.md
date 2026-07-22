# ADR 064 - TF-IDF Implemented from Scratch

## Status

Accepted

## Context

Needed keyword importance scoring without scikit-learn dependency to keep the pipeline
lightweight and CI/CD fast.

## Decision

Built TF-IDF using Python math module only.

## Reasons

- No additional dependencies needed
- TF-IDF formula is straightforward: TF × IDF
- Sufficient for financial news keyword extraction
- Easy to understand and maintain
- Works on small news corpora (5-20 articles)

## Consequences

- Slower than scikit-learn TfidfVectorizer for large corpora
- No sparse matrix optimization
- Future: use scikit-learn for corpora > 1000 documents
