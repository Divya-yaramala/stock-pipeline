.PHONY: setup up down logs ps airflow-ui dbt-run dbt-test backfill clean help dashboard

# ── Environment ───────────────────────────────────────────────────────────────
include .env
export

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

setup: ## Create .env and generate Airflow keys
	@bash scripts/setup.sh

# ── Docker ────────────────────────────────────────────────────────────────────
up: ## Start all services (build first)
	docker compose up --build -d
	@echo "Airflow UI → http://localhost:8080 (admin / admin)"

down: ## Stop all services
	docker compose down

logs: ## Tail logs for all services
	docker compose logs -f --tail=100

ps: ## Show service status
	docker compose ps

# ── Airflow ───────────────────────────────────────────────────────────────────
airflow-ui: ## Open Airflow UI in the browser
	open http://localhost:8080 || xdg-open http://localhost:8080

trigger: ## Trigger a manual DAG run
	docker compose exec airflow-scheduler \
		airflow dags trigger stock_price_pipeline

# ── dbt (runs inside the scheduler container) ─────────────────────────────────
dbt-deps: ## Install dbt packages
	docker compose exec airflow-scheduler \
		bash -c "cd /opt/dbt/stock_analytics && dbt deps --profiles-dir /opt/dbt/stock_analytics"

dbt-run: ## Run all dbt models
	docker compose exec airflow-scheduler \
		bash -c "cd /opt/dbt/stock_analytics && dbt run --profiles-dir /opt/dbt/stock_analytics"

dbt-test: ## Run dbt data quality tests
	docker compose exec airflow-scheduler \
		bash -c "cd /opt/dbt/stock_analytics && dbt test --profiles-dir /opt/dbt/stock_analytics"

dbt-docs: ## Generate and serve dbt documentation (port 8081)
	docker compose exec airflow-scheduler \
		bash -c "cd /opt/dbt/stock_analytics && dbt docs generate --profiles-dir /opt/dbt/stock_analytics && dbt docs serve --port 8081"

# ── Backfill ─────────────────────────────────────────────────────────────────
# Usage: make backfill START=2024-01-01 END=2024-03-31
backfill: ## Backfill the DAG between START and END dates
	docker compose exec airflow-scheduler \
		airflow dags backfill stock_price_pipeline \
			--start-date $(START) \
			--end-date   $(END)

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: ## Remove all Docker volumes (DESTROYS DATA)
	docker compose down -v

# ── Local Dev ─────────────────────────────────────────────────────────────────
test: ## Run all 108 tests
	pytest tests/ -v

lint: ## Run flake8 linting
	flake8 ingestion/ scripts/ tests/ --max-line-length=100 --ignore=E402,W503

format: ## Format code with black and isort
	black ingestion/ scripts/ tests/
	isort ingestion/ scripts/ tests/

typecheck: ## Run mypy type checking
	mypy ingestion/ --ignore-missing-imports

run: ## Run full pipeline locally
	python scripts/run_pipeline_local.py

health: ## Check health of all services
	python scripts/health_check.py

cost: ## Estimate monthly S3 storage cost
	python -c "from ingestion.s3_optimizer import generate_cost_report; import os; print(generate_cost_report(os.getenv('AWS_BUCKET_NAME')))"

validate: ## Validate all required environment variables
	python scripts/validate_secrets.py

backfill: ## Backfill missing data (usage: make backfill START=2024-01-01 END=2024-01-31)
	python scripts/backfill.py --start-date $(START) --end-date $(END)

# ── Dashboard ─────────────────────────────────────────────────────────────────
dashboard: ## Start Streamlit dashboard locally (port 8503)
	streamlit run dashboard/app.py --server.port=8503
