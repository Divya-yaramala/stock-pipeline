from unittest.mock import MagicMock, patch

from scripts.health_check import (
    check_postgres_connectivity,
    check_s3_connectivity,
)


def test_check_s3_healthy():
    with patch("scripts.health_check.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        result = check_s3_connectivity()
    assert result["service"] == "S3"
    assert result["status"] == "healthy"


def test_check_s3_unhealthy():
    with patch("scripts.health_check.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.side_effect = Exception("access denied")
        mock_boto3.client.return_value = mock_s3
        result = check_s3_connectivity()
    assert result["service"] == "S3"
    assert result["status"] == "unhealthy"


def test_check_postgres_healthy():
    with patch("scripts.health_check.psycopg2") as mock_psycopg2:
        mock_conn = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        result = check_postgres_connectivity()
    assert result["service"] == "Postgres"
    assert result["status"] == "healthy"


def test_check_postgres_unhealthy():
    with patch("scripts.health_check.psycopg2") as mock_psycopg2:
        mock_psycopg2.connect.side_effect = Exception("connection refused")
        result = check_postgres_connectivity()
    assert result["service"] == "Postgres"
    assert result["status"] == "unhealthy"
