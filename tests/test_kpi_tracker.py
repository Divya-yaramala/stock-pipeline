from unittest.mock import MagicMock, patch

from ingestion.kpi_tracker import (
    generate_kpi_dashboard,
    get_kpi_status,
    record_kpi,
)


def test_get_kpi_status_on_track():
    # K002: pipeline_success_rate, target=95.0, higher_is_better; 95.0 >= 95*0.95=90.25
    result = get_kpi_status("K002", 95.0)
    assert result == "on_track"


def test_get_kpi_status_off_track():
    # K002: pipeline_success_rate, target=95.0; 60.0 < 95*0.80=76.0
    result = get_kpi_status("K002", 60.0)
    assert result == "off_track"


def test_record_kpi_success():
    with patch("ingestion.kpi_tracker.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        result = record_kpi("K001", 20.0, "test-bucket", "2026-06-27")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_generate_kpi_dashboard_structure():
    with patch("ingestion.kpi_tracker.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.side_effect = Exception("NoSuchKey")
        result = generate_kpi_dashboard("test-bucket", "2026-06-27")
    assert isinstance(result, dict)
    assert "kpis" in result


def test_get_kpi_status_at_risk():
    # K002: pipeline_success_rate, target=95.0; 82.0 is in [76.0, 90.25) → at_risk
    result = get_kpi_status("K002", 82.0)
    assert result == "at_risk"
