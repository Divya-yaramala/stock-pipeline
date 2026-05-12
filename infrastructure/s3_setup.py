import logging

import boto3
from botocore.exceptions import ClientError
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(path: str = "config/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def create_bucket_if_not_exists(bucket: str, region: str) -> None:
    s3 = boto3.client("s3", region_name=region)
    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket)
        else:
            s3.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        logger.info(f"Created bucket: {bucket}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
            logger.info(f"Bucket already exists: {bucket}")
        else:
            raise


def create_snowflake_stage_sql(bucket: str, prefix: str, stage: str) -> str:
    return f"""
CREATE OR REPLACE STAGE {stage}
  URL = 's3://{bucket}/{prefix}/'
  CREDENTIALS = (AWS_KEY_ID = '{{AWS_KEY_ID}}' AWS_SECRET_KEY = '{{AWS_SECRET_KEY}}')
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);
"""


def setup(config_path: str = "config/config.yaml") -> None:
    cfg = load_config(config_path)
    bucket = cfg["aws"]["s3_bucket"]
    region = cfg["aws"]["region"]
    prefix = cfg["aws"]["s3_prefix"]
    stage = cfg["snowflake"]["stage"]

    create_bucket_if_not_exists(bucket, region)

    stage_sql = create_snowflake_stage_sql(bucket, prefix, stage)
    logger.info("Run the following SQL in Snowflake to create the external stage:")
    print(stage_sql)


if __name__ == "__main__":
    setup()
