import logging
import os

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
        logger.info("Created bucket: %s", bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
            logger.info("Bucket already exists: %s", bucket)
        else:
            raise


def setup() -> None:
    bucket = os.environ["AWS_BUCKET_NAME"]
    region = os.environ.get("AWS_REGION", "us-east-1")
    create_bucket_if_not_exists(bucket, region)


if __name__ == "__main__":
    setup()
