# ADR 079 - Knowledge Graph for Domain Knowledge

## Status
Accepted

## Context
The pipeline needed a way to represent domain relationships between stocks, sectors, and market entities. A flat table of tickers captures price data but not the semantic relationships — which stocks compete, which are correlated, which belong to the same sector — that are essential for contextual analysis and recommendation.

## Decision
Built an S3-based knowledge graph with typed entities (stock, sector, market) and typed relationships (BELONGS_TO, COMPETES_WITH, CORRELATES_WITH). Entities and relationships are stored as individual JSON files under a structured S3 prefix.

## Reasons
- Graph structure captures domain relationships naturally — sector membership, competition, and price correlation are fundamentally graph concepts
- BELONGS_TO, COMPETES_WITH, CORRELATES_WITH cover the key relationship types needed for stock domain analysis
- S3 storage requires no graph database infrastructure — zero additional cost or operational complexity
- Entity traversal enables discovery of related stocks (e.g., "find all stocks in the same sector as AAPL")
- Complements the correlation matrix (numeric relationships) with semantic relationships (typed, named edges)

## Consequences
- Simple adjacency list stored as S3 files — not optimized for complex multi-hop graph queries
- No built-in graph traversal algorithms (BFS/DFS) — must implement manually if needed
- Scanning all relationship files for a query is O(n) — acceptable for 5 tickers, not at scale
- Future: migrate to Amazon Neptune for production graph queries at scale
