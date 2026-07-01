from unittest.mock import MagicMock, patch

from ingestion.impact_analyzer import (
    analyze_data_quality_impact,
    analyze_schema_change_impact,
    generate_impact_report,
)


def test_analyze_schema_change_impact_structure():
    with patch(
        "ingestion.impact_analyzer.find_impacted_datasets", return_value=["validated_prices"]
    ):
        result = analyze_schema_change_impact("raw_prices", ["volume", "open"], "test-bucket")
    assert "impacted_count" in result


def test_analyze_schema_change_severity_low():
    with patch(
        "ingestion.impact_analyzer.find_impacted_datasets",
        return_value=["validated_prices", "anomaly_results"],
    ):
        result = analyze_schema_change_impact("raw_prices", ["volume"], "test-bucket")
    assert result["severity"] == "low"


def test_analyze_schema_change_severity_high():
    datasets = [
        "validated_prices",
        "anomaly_results",
        "predictions",
        "sentiment_scores",
        "postgres_staging",
        "snowflake_raw",
        "snowflake_marts",
        "reports",
    ]
    with patch("ingestion.impact_analyzer.find_impacted_datasets", return_value=datasets):
        result = analyze_schema_change_impact("raw_prices", ["volume"], "test-bucket")
    assert result["severity"] == "high"


def test_analyze_data_quality_impact_high_risk():
    with patch(
        "ingestion.impact_analyzer.find_impacted_datasets",
        return_value=["validated_prices", "anomaly_results"],
    ):
        result = analyze_data_quality_impact("raw_prices", 60.0, "test-bucket")
    assert result["risk_level"] == "high"


def test_generate_impact_report_structure():
    with patch("ingestion.impact_analyzer.find_impacted_datasets", return_value=[]):
        with patch("ingestion.impact_analyzer.boto3") as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.client.return_value = mock_s3
            result = generate_impact_report("schema_change", "raw_prices", "test-bucket")
    assert "trigger" in result
