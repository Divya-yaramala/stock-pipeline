from unittest.mock import MagicMock, patch

from ingestion.resource_manager import (
    check_resource_thresholds,
    get_system_resources,
    should_run_pipeline,
)


def _make_psutil_mocks(
    cpu=10.0, memory_pct=50.0, memory_avail_gb=8.0, disk_pct=60.0, disk_free_gb=100.0
):
    mock_mem = MagicMock()
    mock_mem.percent = memory_pct
    mock_mem.available = int(memory_avail_gb * 1024**3)

    mock_disk = MagicMock()
    mock_disk.percent = disk_pct
    mock_disk.free = int(disk_free_gb * 1024**3)

    return cpu, mock_mem, mock_disk


def test_get_system_resources_structure():
    cpu, mock_mem, mock_disk = _make_psutil_mocks()
    with patch("ingestion.resource_manager.psutil.cpu_percent", return_value=cpu), patch(
        "ingestion.resource_manager.psutil.virtual_memory", return_value=mock_mem
    ), patch("ingestion.resource_manager.psutil.disk_usage", return_value=mock_disk):
        result = get_system_resources()

    assert "cpu_percent" in result
    assert "memory_percent" in result
    assert "disk_usage_percent" in result
    assert "memory_available_gb" in result
    assert "disk_free_gb" in result


def test_check_resource_thresholds_ok():
    cpu, mock_mem, mock_disk = _make_psutil_mocks(cpu=30.0, memory_pct=50.0, disk_pct=60.0)
    with patch("ingestion.resource_manager.psutil.cpu_percent", return_value=cpu), patch(
        "ingestion.resource_manager.psutil.virtual_memory", return_value=mock_mem
    ), patch("ingestion.resource_manager.psutil.disk_usage", return_value=mock_disk):
        result = check_resource_thresholds()

    assert result["cpu"]["status"] == "ok"
    assert result["memory"]["status"] == "ok"
    assert result["disk"]["status"] == "ok"


def test_check_resource_thresholds_critical():
    cpu, mock_mem, mock_disk = _make_psutil_mocks(cpu=30.0, memory_pct=50.0, disk_pct=95.0)
    with patch("ingestion.resource_manager.psutil.cpu_percent", return_value=cpu), patch(
        "ingestion.resource_manager.psutil.virtual_memory", return_value=mock_mem
    ), patch("ingestion.resource_manager.psutil.disk_usage", return_value=mock_disk):
        result = check_resource_thresholds()

    assert result["disk"]["status"] == "critical"


def test_should_run_pipeline_true():
    cpu, mock_mem, mock_disk = _make_psutil_mocks(cpu=20.0, memory_pct=40.0, disk_pct=50.0)
    with patch("ingestion.resource_manager.psutil.cpu_percent", return_value=cpu), patch(
        "ingestion.resource_manager.psutil.virtual_memory", return_value=mock_mem
    ), patch("ingestion.resource_manager.psutil.disk_usage", return_value=mock_disk):
        result = should_run_pipeline()

    assert result is True


def test_should_run_pipeline_false():
    cpu, mock_mem, mock_disk = _make_psutil_mocks(cpu=20.0, memory_pct=40.0, disk_pct=95.0)
    with patch("ingestion.resource_manager.psutil.cpu_percent", return_value=cpu), patch(
        "ingestion.resource_manager.psutil.virtual_memory", return_value=mock_mem
    ), patch("ingestion.resource_manager.psutil.disk_usage", return_value=mock_disk):
        result = should_run_pipeline()

    assert result is False
