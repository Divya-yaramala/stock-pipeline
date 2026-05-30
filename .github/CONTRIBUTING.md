# Contributing

## Running Tests Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run all 108 tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=ingestion --cov-report=term-missing

# Run a specific test file
pytest tests/test_anomaly_detector.py -v
```

## Code Style Requirements

This project enforces consistent formatting via CI. Before opening a PR, run:

```bash
# Format code
black ingestion/ tests/
isort ingestion/ tests/

# Check linting
flake8 ingestion/ tests/

# Check type annotations
mypy ingestion/
```

All four checks must pass cleanly. The CI pipeline (`code-quality.yml`) will fail the PR if any check fails.

Settings are in `pyproject.toml`:
- `black`: line length 88
- `isort`: black-compatible profile
- `flake8`: max line length 88, ignores E203/W503
- `mypy`: strict mode

## How to Add a New Ticker

1. Open `ingestion/fetch_stocks.py` and add the ticker symbol to the `TICKERS` list.
2. Open `ingestion/config_manager.py` and add it to the `tickers` field in `PipelineConfig`.
3. Add a corresponding fixture to `tests/test_fetch_stocks.py` covering fetch and S3 upload.
4. Run `pytest tests/test_fetch_stocks.py -v` to confirm the new tests pass.
5. Update `docs/data-dictionary.md` if the ticker has unique characteristics worth noting.

## How to Add a New Pipeline Step

1. Create a new module in `ingestion/` following the existing pattern:
   - Accept a `config: PipelineConfig` argument
   - Return a typed result dict
   - Send failures to `dead_letter_queue.record_failure()`
   - Record lineage with `lineage_tracker.record_step()`

2. Write unit tests in `tests/test_<module_name>.py`. Aim for at least 6 tests covering:
   - Happy path
   - Empty input handling
   - S3 read/write mocking
   - Error path (DLQ capture)

3. Wire the step into `dags/stock_price_pipeline.py`:
   - Add a `PythonOperator` task
   - Set correct upstream dependencies with `>>` chaining

4. Update the DAG task count in the README and the progress log.

5. Run the full test suite before opening a PR:
   ```bash
   pytest tests/ -v
   ```
