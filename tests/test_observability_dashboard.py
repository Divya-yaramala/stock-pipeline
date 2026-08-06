from unittest.mock import MagicMock, patch

from ingestion.observability_dashboard import (
    calculate_golden_signals,
    check_slo_compliance,
    generate_observability_report,
    get_service_level_objectives,
)


def test_calculate_golden_signals_structure():
    metrics = {
        "pipeline_duration_minutes": 5.0,
        "records_processed": 5,
        "error_count": 0,
        "cpu_utilization_pct": 45.0,
    }
    result = calculate_golden_signals(metrics)
    assert "latency" in result
    assert "traffic" in result
    assert "errors" in result
    assert "saturation" in result


def test_get_service_level_objectives_count():
    slos = get_service_level_objectives()
    assert len(slos) == 5


def test_check_slo_compliance_structure():
    metrics = {
        "sla_compliance_pct": 99.9,
        "data_age_hours": 5.0,
        "quality_score": 95.0,
        "prediction_accuracy_pct": 85.0,
        "api_p95_latency_ms": 100.0,
    }
    result = check_slo_compliance(metrics)
    assert "compliant" in result
    assert "total" in result


def test_generate_observability_report_structure():
    with patch("ingestion.observability_dashboard.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [{"Contents": []}]
        mock_s3.get_paginator.return_value = paginator
        mock_client.return_value = mock_s3
        result = generate_observability_report("test-bucket", "2026-08-06")
    assert "golden_signals" in result


def test_check_slo_compliance_violation():
    metrics = {
        "sla_compliance_pct": 99.9,
        "data_age_hours": 5.0,
        "quality_score": 60.0,
        "prediction_accuracy_pct": 85.0,
        "api_p95_latency_ms": 100.0,
    }
    result = check_slo_compliance(metrics)
    assert len(result["violations"]) > 0
