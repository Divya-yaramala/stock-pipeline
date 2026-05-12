from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator

default_args = {
    "owner": "divya",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "email": ["divyayaramala145@gmail.com"],
}

COPY_INTO_SQL = """
COPY INTO STOCK_DB.RAW.RAW_STOCK_PRICES
FROM @S3_STAGE
FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1)
ON_ERROR = 'CONTINUE';
"""

with DAG(
    dag_id="stock_price_pipeline",
    default_args=default_args,
    description="Daily stock price ingestion: S3 → Snowflake → dbt",
    schedule_interval="0 18 * * 1-5",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["stock", "data-engineering"],
) as dag:

    fetch_and_upload = PythonOperator(
        task_id="fetch_and_upload_to_s3",
        python_callable=lambda: __import__(
            "ingestion.fetch_stock_prices", fromlist=["run"]
        ).run(),
    )

    load_to_snowflake = SnowflakeOperator(
        task_id="load_raw_to_snowflake",
        snowflake_conn_id="snowflake_default",
        sql=COPY_INTO_SQL,
    )

    run_dbt = BashOperator(
        task_id="run_dbt_models",
        bash_command="cd /opt/airflow/dbt && dbt run --target prod",
    )

    test_dbt = BashOperator(
        task_id="test_dbt_models",
        bash_command="cd /opt/airflow/dbt && dbt test --target prod",
    )

    fetch_and_upload >> load_to_snowflake >> run_dbt >> test_dbt
