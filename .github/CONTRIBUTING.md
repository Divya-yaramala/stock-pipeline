# Contributing

## Running Tests Locally
pytest tests/ -v

## Code Style Requirements
black ingestion/ scripts/ tests/ api/
isort ingestion/ scripts/ tests/ api/
flake8 ingestion/ scripts/ tests/ api/ --max-line-length=100
mypy ingestion/ --ignore-missing-imports

## Adding a New Ingestion Module
1. Create ingestion/your_module.py
2. Add type hints to all functions
3. Create tests/test_your_module.py with 5+ tests
4. Update docs/project-stats.md
5. Add ADR if a major decision was made

## Adding a New Airflow Task
1. Add task to airflow/dags/stock_pipeline_dag.py
2. Import from ingestion module
3. Chain dependencies correctly
4. Update docs/pipeline-overview.md
