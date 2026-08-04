from unittest.mock import MagicMock, patch

from ingestion.delta_versioner import (
    create_delta_log_entry,
    get_delta_history,
    get_table_version,
    optimize_delta_table,
    run_delta_versioning,
)


def test_create_delta_log_entry_returns_id():
    with patch("ingestion.delta_versioner.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        result = create_delta_log_entry("INSERT", "AAPL", 5, 0, False, "test-bucket")
    assert isinstance(result, str)
    assert len(result) > 0
    mock_s3.put_object.assert_called_once()


def test_get_delta_history_returns_list():
    with patch("ingestion.delta_versioner.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.get_paginator.return_value.paginate.return_value = [{"Contents": []}]
        result = get_delta_history("AAPL", "test-bucket", days=7)
    assert isinstance(result, list)


def test_get_table_version_structure():
    with patch("ingestion.delta_versioner.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.get_paginator.return_value.paginate.return_value = [{"Contents": []}]
        result = get_table_version("AAPL", "test-bucket")
    assert "current_version" in result
    assert result["current_version"] == 0
    assert "total_records" in result


def test_optimize_delta_table_structure():
    with patch("ingestion.delta_versioner.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.get_paginator.return_value.paginate.return_value = [{"Contents": []}]
        result = optimize_delta_table("AAPL", "test-bucket")
    assert "files_compacted" in result
    assert result["files_compacted"] == 0


def test_run_delta_versioning_returns_id():
    with patch("ingestion.delta_versioner.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        result = run_delta_versioning("AAPL", "INSERT", 5, "test-bucket")
    assert isinstance(result, str)
    assert len(result) > 0
