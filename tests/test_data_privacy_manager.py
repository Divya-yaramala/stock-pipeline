from unittest.mock import MagicMock, patch

from ingestion.data_privacy_manager import (
    anonymize_dataset,
    check_policy_compliance,
    generate_privacy_report,
    get_privacy_policy,
)


def test_get_privacy_policy_found():
    result = get_privacy_policy("financial_data")
    assert result is not None
    assert "policy_id" in result


def test_get_privacy_policy_not_found():
    result = get_privacy_policy("nonexistent_policy")
    assert result is None


def test_check_policy_compliance_compliant():
    metadata = {"classification": "CONFIDENTIAL", "retention_days": 365, "has_pii": False}
    result = check_policy_compliance("financial_data", metadata)
    assert result["compliant"] is True


def test_anonymize_dataset_hashes_fields():
    data = [{"email": "user@example.com", "ticker": "AAPL"}]
    result = anonymize_dataset(data, ["email"])
    assert result[0]["email"] != "user@example.com"
    assert result[0]["ticker"] == "AAPL"


def test_generate_privacy_report_structure():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.data_privacy_manager.boto3.client", return_value=mock_client):
        result = generate_privacy_report("test-bucket")
    assert isinstance(result, dict)
    assert "total_datasets" in result
