"""
Health check for the stock-price pipeline stack.
Usage: python scripts/check_airflow.py
Checks: Airflow webserver, Postgres connection, DAG file validity.
"""
import os
import sys
import py_compile
import tempfile
import logging
from pathlib import Path

logging.basicConfig(level=logging.WARNING)

AIRFLOW_URL  = "http://localhost:8080"
DAGS_DIR     = Path(__file__).parent.parent / "airflow" / "dags"
GREEN = "\033[92m✅"
RED   = "\033[91m❌"
RESET = "\033[0m"


def _check_webserver() -> bool:
    try:
        import requests
        resp = requests.get(f"{AIRFLOW_URL}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def _check_postgres() -> bool:
    try:
        import psycopg2
        psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            user=os.environ.get("POSTGRES_USER", "pipeline_user"),
            password=os.environ.get("POSTGRES_PASSWORD", ""),
            dbname=os.environ.get("POSTGRES_DB", "stock_pipeline"),
            connect_timeout=5,
        ).close()
        return True
    except Exception:
        return False


def _check_dag_files() -> tuple[bool, list[str]]:
    errors = []
    dag_files = list(DAGS_DIR.glob("*.py"))
    if not dag_files:
        return False, ["No DAG files found"]
    for path in dag_files:
        if path.name.startswith("_"):
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{path.name}: {exc}")
    return len(errors) == 0, errors


def _status(ok: bool, label_ok: str, label_fail: str) -> str:
    if ok:
        return f"{GREEN} {label_ok}{RESET}"
    return f"{RED} {label_fail}{RESET}"


def run_checks() -> None:
    print("\n── Stock Pipeline Health Check ──────────────────────")

    web_ok  = _check_webserver()
    pg_ok   = _check_postgres()
    dag_ok, dag_errors = _check_dag_files()

    print(f"Airflow Webserver : {_status(web_ok,  'Running',    'Not running')}")
    print(f"Postgres          : {_status(pg_ok,   'Connected',  'Not connected')}")
    print(f"DAG files         : {_status(dag_ok,  'Valid',       'Errors found')}")

    if dag_errors:
        for err in dag_errors:
            print(f"  {RED} {err}{RESET}")

    print("─────────────────────────────────────────────────────\n")

    if not all([web_ok, pg_ok, dag_ok]):
        sys.exit(1)


if __name__ == "__main__":
    run_checks()
