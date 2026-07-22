# NLP Guide — Stock Pipeline

## Overview
The pipeline includes custom NLP capabilities built with
pure Python — no external NLP libraries required.

## Financial Domain Terms (15 terms)

| Term | Sentiment | Usage |
|---|---|---|
| bullish | positive | "Market is bullish on AAPL" |
| bearish | negative | "Bearish outlook for tech" |
| rally | positive | "Stock rally continues" |
| selloff | negative | "Market selloff today" |
| surge | positive | "Shares surge after earnings" |
| plunge | negative | "Stock plunges on news" |
| outperform | positive | "MSFT to outperform peers" |
| underperform | negative | "AMZN underperforms sector" |
| upgrade | positive | "Analyst upgrades to Buy" |
| downgrade | negative | "Downgraded to Sell" |
| beat | positive | "Earnings beat estimates" |
| miss | negative | "Revenue miss disappoints" |
| guidance | neutral | "Company raises guidance" |
| forecast | neutral | "Analyst forecast raised" |
| earnings | neutral | "Earnings report due" |

## News Categories

| Category | Keywords |
|---|---|
| earnings | earnings, revenue, profit, EPS |
| merger | acquisition, merger, buyout, deal |
| product | launch, product, release, announce |
| regulatory | SEC, FDA, regulation, fine |
| analyst | upgrade, downgrade, price target |
| macro | Fed, inflation, interest rate, GDP |

## NLP Pipeline Flow
News headline → tokenize_text() → extract_financial_entities()
                               → calculate_text_sentiment()
                               → classify_news_category()
                               → extract_price_targets()
                               → summarize_text()
                               → run_nlp_analysis() → S3

## Text Analytics Flow
News corpus → calculate_tfidf() → find_key_phrases()
                                → classify_news_category()
                                → run_text_analytics() → S3

## Example Analysis
Input: "Apple beat Q3 earnings estimates with strong iPhone sales.
        Goldman Sachs upgraded AAPL to Buy with a price target of $210."

Output:
- Tickers: ["AAPL"]
- Category: "earnings" + "analyst"
- Sentiment: BULLISH (beat + upgrade)
- Price targets: [{"price": 210.0}]
- Key terms: ["beat", "upgrade"]

## Limitations
- No context understanding (sarcasm not detected)
- Simple regex for entity extraction
- 15 financial terms may miss domain-specific language
- Future: integrate FinBERT for production-grade NLP
