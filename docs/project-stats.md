# Project Statistics — AI-Powered Stock Price Pipeline

## Code Statistics
| Metric | Count |
|---|---|
| Python files | 15 ingestion modules + 6 scripts |
| Test files | 14 test files |
| Total tests | 108 passing |
| dbt models | 6 models (3 staging + 3 marts) |
| Airflow tasks | 13 tasks in DAG |
| ADRs | 7 architecture decisions |
| Lines of Python code | ~2500+ |

## Pipeline Statistics
| Component | Details |
|---|---|
| Tickers tracked | 5 (AAPL, MSFT, GOOGL, AMZN, TSLA) |
| Daily API calls | 5 tickers × 4 AI steps = 20 calls |
| S3 prefixes | raw/, processed/, errors/, lineage/, monitoring/, reports/ |
| Postgres tables | 4 staging tables |
| Snowflake schemas | RAW, STAGING, MARTS |
| dbt tests | not_null + unique on all key columns |

## AI Components
| Component | Algorithm | Output |
|---|---|---|
| Anomaly Detection | Isolation Forest | is_anomaly + anomaly_score |
| Price Prediction | Facebook Prophet | 5-day forecast with confidence bounds |
| Market Insights | GPT-3.5-turbo | 3-sentence daily summary |

## Production Patterns Implemented
1. Idempotent loading (ON CONFLICT DO NOTHING)
2. Dead letter queue (failed record capture + replay)
3. Data validation (7-point quality checks)
4. SLA monitoring (per-step time thresholds)
5. Data lineage tracking (full audit trail)
6. Slack alerting (real-time notifications)
7. Cost optimization (S3 archiving)
8. Resource management (CPU/memory/disk checks)
9. Incremental loading (auto gap detection)
10. Retry logic (tenacity for API calls)

## Development Statistics
| Metric | Count |
|---|---|
| Days of development | 25 days |
| Total commits | 150+ |
| CI/CD workflows | 2 (CI + Code Quality) |
| Linters passing | 4 (black, isort, flake8, mypy) |
| Documentation files | 8 |

## Why This Stack Beats Alternatives
| Our Choice | Alternative | Why We Won |
|---|---|---|
| Airflow | Prefect | Industry standard, more job postings |
| Snowflake | Redshift | Better dbt integration, cost flexibility |
| dbt | Custom SQL | Built-in tests, lineage, version control |
| Prophet | ARIMA | Handles missing data, easier to configure |
| Isolation Forest | Z-score | Multivariate, no labeled data needed |
| GitHub Actions | Jenkins | Free, native GitHub integration |
