from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from ingestion.s3_optimizer import (
    archive_old_raw_data,
    delete_old_monitoring_data,
    generate_cost_report,
    get_s3_storage_summary,
)


def _make_s3_object(key: str, size: int, days_old: int = 0):
    from datetime import timedelta

    last_modified = datetime.now(tz=timezone.utc) - timedelta(days=days_old)
    return {"Key": key, "Size": size, "LastModified": last_modified}


def test_get_s3_storage_summary_structure():
    page = {"Contents": [_make_s3_object("raw/stocks/2026/01/01/AAPL.json", 1024)]}
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [page]
    mock_s3 = MagicMock()
    mock_s3.get_paginator.return_value = mock_paginator

    with patch("ingestion.s3_optimizer.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_s3
        result = get_s3_storage_summary("test-bucket")

    assert "total_gb" in result
    assert "total_mb" in result
    assert "breakdown_mb" in result


def test_generate_cost_report_structure():
    page = {"Contents": [_make_s3_object("raw/stocks/2026/01/01/AAPL.json", 1024**3)]}
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [page]
    mock_s3 = MagicMock()
    mock_s3.get_paginator.return_value = mock_paginator

    with patch("ingestion.s3_optimizer.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_s3
        report = generate_cost_report("test-bucket")

    assert "storage_gb" in report
    assert "estimated_monthly_cost_usd" in report
    assert "breakdown_by_prefix" in report


def test_archive_old_raw_data_success():
    old_obj = _make_s3_object("raw/stocks/2026/01/01/AAPL.json", 512, days_old=40)
    page = {"Contents": [old_obj]}
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [page]
    mock_s3 = MagicMock()
    mock_s3.get_paginator.return_value = mock_paginator

    with patch("ingestion.s3_optimizer.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_s3
        count = archive_old_raw_data("test-bucket", days_to_keep=30)

    assert count == 1
    mock_s3.copy_object.assert_called_once()
    mock_s3.delete_object.assert_called_once()


def test_archive_old_raw_data_empty():
    page = {"Contents": []}
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [page]
    mock_s3 = MagicMock()
    mock_s3.get_paginator.return_value = mock_paginator

    with patch("ingestion.s3_optimizer.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_s3
        count = archive_old_raw_data("test-bucket", days_to_keep=30)

    assert count == 0


def test_delete_old_monitoring_data_success():
    old_obj = _make_s3_object("monitoring/reports/2026/01/01/report.json", 256, days_old=10)
    page = {"Contents": [old_obj]}
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [page]
    mock_s3 = MagicMock()
    mock_s3.get_paginator.return_value = mock_paginator

    with patch("ingestion.s3_optimizer.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_s3
        count = delete_old_monitoring_data("test-bucket", days_to_keep=7)

    assert count == 1
    mock_s3.delete_object.assert_called_once()
