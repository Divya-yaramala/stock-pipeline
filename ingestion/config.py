import os

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
S3_BUCKET = os.getenv("AWS_BUCKET_NAME", "")
S3_PREFIX = "raw/stocks"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DATE_FORMAT = "%Y/%m/%d"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
