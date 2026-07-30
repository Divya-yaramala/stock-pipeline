# ADR 080 - Semantic Search with Inverted Index

## Status
Accepted

## Context
With 99 modules and 79 ADRs, developers need a way to quickly find relevant code and documentation without reading every file. A searchable index over pipeline documentation reduces onboarding time and makes the codebase more navigable.

## Decision
Built a custom inverted index using pure Python. Documents (module descriptions, ADR summaries, README sections) are tokenized, stopwords removed, and indexed as `{term: [doc_ids]}`. Queries are scored by summing term frequency matches across documents.

## Reasons
- Inverted index is the foundation of all search engines — a proven, well-understood approach
- Pure Python implementation requires no Elasticsearch, OpenSearch, or external search infrastructure
- TF-based ranking is sufficient for a small document corpus (under 200 documents)
- Pipeline documentation search helps developers find relevant modules without grepping the codebase
- Module recommendation reduces time to find related code and understand component relationships

## Consequences
- No semantic similarity — only keyword matching (typing "forecasting" won't find documents about "prediction")
- Index must be rebuilt when new modules are added (not automatically updated)
- TF ranking ignores document length — longer documents may unfairly score higher
- Future: add word embeddings (e.g., sentence-transformers) for semantic similarity beyond keyword overlap
