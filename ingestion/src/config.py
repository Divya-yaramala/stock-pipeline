import os

STOCK_SYMBOLS: list[str] = os.getenv(
    "STOCK_SYMBOLS", "AAPL,MSFT,GOOGL,AMZN,META,TSLA,NVDA,JPM,JNJ,V"
).split(",")

S3_BUCKET: str = os.getenv("S3_BUCKET", "")
S3_PREFIX: str = os.getenv("S3_PREFIX", "raw/stocks")
AWS_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

WAREHOUSE_HOST: str = os.getenv("WAREHOUSE_HOST", "localhost")
WAREHOUSE_PORT: int = int(os.getenv("WAREHOUSE_PORT", "5432"))
WAREHOUSE_USER: str = os.getenv("WAREHOUSE_USER", "pipeline_user")
WAREHOUSE_PASSWORD: str = os.getenv("WAREHOUSE_PASSWORD", "")
WAREHOUSE_DB: str = os.getenv("WAREHOUSE_DB", "warehouse")
