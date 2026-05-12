.PHONY: setup up down logs ps airflow-ui dbt-run dbt-test backfill clean help

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
