# Knowledge Graph Guide — Stock Pipeline

## Overview
The pipeline maintains a knowledge graph capturing semantic
relationships between stocks, sectors, and market entities.

## Entity Types

| Type | Examples | Properties |
|---|---|---|
| stock | AAPL, MSFT, GOOGL | ticker, name, sector, market_cap |
| sector | Technology, Communication Services | name, benchmark_return |
| market | US_EQUITIES | name, trading_hours |
| metric | quality_score, anomaly_rate | name, unit, threshold |

## Relationship Types

| Relationship | Example | Properties |
|---|---|---|
| BELONGS_TO | AAPL → Technology | since_date |
| COMPETES_WITH | AAPL ↔ MSFT | competition_level |
| CORRELATES_WITH | AAPL → MSFT | correlation_score |
| TRACKED_BY | AAPL → quality_score | since_date |
| PART_OF | Technology → US_EQUITIES | weight |

## Stock Knowledge Graph (built-in)
```
AAPL ──BELONGS_TO──→ Technology
MSFT ──BELONGS_TO──→ Technology
GOOGL ──BELONGS_TO──→ Communication Services
AMZN ──BELONGS_TO──→ Consumer Discretionary
TSLA ──BELONGS_TO──→ Consumer Discretionary

AAPL ──COMPETES_WITH──→ MSFT (same sector)
AAPL ──CORRELATES_WITH──→ MSFT (Pearson > 0.7)
```

## Semantic Search Index

### Indexed Documents
- Module docstrings (99 modules)
- ADR decisions and rationale
- README sections
- Pipeline overview sections

### Search Algorithm
1. Tokenize query → remove stopwords → lowercase
2. Look up each term in inverted index
3. Score = sum of term frequencies across documents
4. Return top_k by score

### Example Searches
```
"anomaly detection machine learning"
→ Returns: anomaly_detector.py, ensemble_model.py, drift_detector.py

"kafka streaming real-time"
→ Returns: stock_kafka_producer.py, stock_kafka_consumer.py

"data quality validation"
→ Returns: data_validator.py, quality_scorer.py, quality_gate.py
```

## Building the Knowledge Graph
```python
python -c "
from ingestion.knowledge_graph import build_stock_knowledge_graph
import os
result = build_stock_knowledge_graph(os.getenv('AWS_BUCKET_NAME'))
print('Knowledge graph built:', result)
"
```

## Searching Documentation
```python
python -c "
from ingestion.semantic_search import search_pipeline_knowledge
import os
results = search_pipeline_knowledge('portfolio optimization sharpe ratio', os.getenv('AWS_BUCKET_NAME'))
print('Top results:')
for r in results[:5]:
    print(f'  {r[\"id\"]}: score={r[\"score\"]}')
"
```
