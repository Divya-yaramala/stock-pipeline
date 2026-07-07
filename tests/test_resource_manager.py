from unittest.mock import MagicMock, patch

from ingestion.resource_manager import (
    check_resource_health,
    estimate_pipeline_resources,
    get_system_metrics,
    run_resource_check,
)


def _make_psutil_mocks(cpu: float = 10.0, memory_pct: float = 50.0, disk_pct: float = 60.0):
    mock_mem = MagicMock()
    mock_mem.percent = memory_pct

    mock_disk = MagicMock()
    mock_disk.percent = disk_pct

    return cpu, mock_mem, mock_disk


def test_get_system_metrics_structure():
    cpu, mock_mem, mock_disk = _make_psutil_mocks()
    with patch("ingestion.resource_manager.psutil.cpu_percent", return_value=cpu), patch(
        "ingestion.resource_manager.psutil.virtual_memory", return_value=mock_mem
    ), patch("ingestion.resource_manager.psutil.disk_usage", return_value=mock_disk):
        result = get_system_metrics()

    assert "cpu_pct" in result
    assert "memory_pct" in result
    assert "disk_pct" in result


def test_check_resource_health_healthy():
    metrics = {"cpu_pct": 30.0, "memory_pct": 50.0, "disk_pct": 60.0}
    result = check_resource_health(metrics)

    assert result["healthy"] is True
    assert len(result["warnings"]) == 0
    assert len(result["critical"]) == 0


def test_check_resource_health_warning():
    metrics = {"cpu_pct": 85.0, "memory_pct": 50.0, "disk_pct": 60.0}
    result = check_resource_health(metrics)

    assert result["healthy"] is False
    assert len(result["warnings"]) > 0


def test_estimate_pipeline_resources_structure():
    result = estimate_pipeline_resources()

    assert "memory_needed_mb" in result
    assert "storage_needed_gb" in result
    assert "api_calls_needed" in result
    assert result["memory_needed_mb"] > 0


def test_run_resource_check_structure():
    cpu, mock_mem, mock_disk = _make_psutil_mocks()
    s3 = MagicMock()
    s3.get_paginator.return_value = MagicMock(paginate=MagicMock(return_value=[{"Contents": []}]))

    with patch("ingestion.resource_manager.psutil.cpu_percent", return_value=cpu), patch(
        "ingestion.resource_manager.psutil.virtual_memory", return_value=mock_mem
    ), patch("ingestion.resource_manager.psutil.disk_usage", return_value=mock_disk), patch(
        "ingestion.resource_manager.boto3.client", return_value=s3
    ):
        result = run_resource_check("my-bucket")

    assert "healthy" in result
    assert "metrics" in result
    assert "s3_quota" in result
