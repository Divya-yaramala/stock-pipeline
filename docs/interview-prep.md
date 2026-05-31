# Interview Preparation — Stock Price Pipeline

## Common Interview Questions and Answers

### Q1: Walk me through your pipeline architecture
Answer: Start with data ingestion from Yahoo Finance API using yfinance library. Raw OHLCV data is uploaded to AWS S3 partitioned by date. From S3 it loads into PostgreSQL staging tables using idempotent inserts. dbt transforms the data into clean staging views and analytics-ready mart tables. The mart data syncs to Snowflake for warehousing. Airflow orchestrates all 13 steps daily at 6 AM UTC. Three AI layers run in parallel: Isolation Forest for anomaly detection, Prophet for price prediction, and GPT-3.5 for market insights.

### Q2: What is idempotency and how did you implement it?
Answer: Idempotency means running the same operation multiple times produces the same result. I implemented it using PostgreSQL's ON CONFLICT (ticker, trade_date) DO NOTHING — if the same record is inserted twice the second insert is silently ignored. I tested this with a dedicated integration test that runs load_to_postgres twice with identical data and asserts no duplicates.

### Q3: What happens when a pipeline step fails?
Answer: Failed records are captured by the Dead Letter Queue module and saved to S3 under errors/YYYY/MM/DD/step/. The DLQ replay task runs at the end of every DAG with TriggerRule.ALL_DONE — meaning it runs even if upstream tasks fail. It loads all failed records and routes them back through the correct pipeline function. Slack alerts fire immediately on failure.

### Q4: How do you ensure data quality?
Answer: Seven-point validation runs after ingestion: row count check, required columns present, no null close prices, positive prices, positive volume, high >= low, and close price within high-low range. Results are scored as a quality percentage. If quality drops below 80% SLA threshold a Slack alert fires and the daily quality report flags the failure.

### Q5: Why did you choose Snowflake over Redshift?
Answer: Three reasons: First, Snowflake separates compute and storage which allows cost optimization — you can pause the warehouse when not in use. Second, dbt has first-class Snowflake support with native env_var() integration. Third, Snowflake is easier to set up without existing AWS infrastructure — important for a portfolio project. I documented this decision in ADR 002.

### Q6: Explain your CI/CD setup
Answer: GitHub Actions runs two workflows on every push to main. The CI workflow installs dependencies, runs flake8 linting, then runs all 108 pytest tests with dummy environment variables. The Code Quality workflow runs black formatting check, isort import sorting, and mypy type checking. Both must pass before code is considered merged. The green badges on the README confirm current status.

### Q7: What is the Dead Letter Queue pattern?
Answer: DLQ is an error handling pattern where failed messages are moved to a separate queue instead of being lost or blocking the pipeline. In my implementation each pipeline module catches per-ticker exceptions and calls send_to_dlq() which saves the failed record as JSON to S3 under errors/YYYY/MM/DD/step/. A replay function at the end of the DAG reprocesses these records. This ensures one bad ticker never blocks the other four.

### Q8: How does your incremental loading work?
Answer: The incremental loader queries PostgreSQL for MAX(trade_date) per ticker. It calculates all missing dates between last loaded date and yesterday. For each missing date it downloads data from yfinance and loads it using the same idempotent insert pattern. This means if the pipeline misses a day it automatically catches up on the next run without any manual intervention.

### Q9: What would you do differently at scale?
Answer: Several things: Replace yfinance with a proper market data API like Polygon.io for reliability. Move from PostgreSQL to a distributed system like Spark for transformation. Use Airflow's KubernetesExecutor instead of LocalExecutor for parallel task execution. Add partitioning to Snowflake tables by trade_date for query performance. Implement proper secrets management with AWS Secrets Manager instead of .env files.

### Q10: How did you track data lineage?
Answer: Each pipeline module calls record_lineage() after successful processing, saving source, destination, transformation name, ticker, and row count to S3 under lineage/YYYY/MM/DD/. The full chain is: yahoo_finance_api → s3_raw → s3_processed_anomalies → s3_processed_predictions → s3_insights → snowflake_marts. This gives a complete audit trail for debugging and compliance.

## Technical Deep Dives

### Isolation Forest Explained
- Unsupervised ML algorithm that isolates anomalies by random feature splitting
- Anomalies require fewer splits to isolate — they get shorter paths in the tree
- contamination=0.05 means we expect 5% of data points to be anomalies
- Uses 5 features: open, high, low, close, volume

### Prophet Explained
- Additive time series model developed by Facebook/Meta
- Handles missing data automatically — no imputation needed
- Built-in seasonality detection for daily/weekly/yearly patterns
- Returns yhat (prediction), yhat_lower, yhat_upper (confidence interval)

### Why 108 Tests?
- 14 test files covering every module
- Mix of unit tests (mock external services) and integration tests
- Tests run in 3-4 seconds locally using mocks
- CI runs them on every push ensuring no regressions

## What I Learned Building This Project

- **Idempotency is non-negotiable** — learned this the hard way by designing insert logic from day one
- **Tests save time** — 108 tests caught regressions every time I refactored code
- **CI/CD changes your workflow** — knowing every push is validated removes anxiety
- **Documentation is code** — ADRs forced me to think deeply about every technology choice
- **AI integration is straightforward** — the hard part is the data pipeline, not the AI layer
