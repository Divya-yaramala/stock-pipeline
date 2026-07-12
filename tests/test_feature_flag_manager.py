import json
from unittest.mock import MagicMock, patch

from ingestion.feature_flag_manager import (
    DEFAULT_FLAGS,
    enable_flag,
    is_enabled,
    load_feature_flags,
    run_flag_audit,
)


def _make_s3_body(data: dict) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return body


def test_load_feature_flags_returns_dict():
    sample = {"enable_gpt_insights": False, "enable_kafka_streaming": True}
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": _make_s3_body(sample)}
    with patch("ingestion.feature_flag_manager.boto3.client", return_value=mock_client):
        result = load_feature_flags("test-bucket")
    assert isinstance(result, dict)
    assert len(result) >= len(sample)


def test_load_feature_flags_uses_defaults():
    mock_client = MagicMock()
    mock_client.get_object.side_effect = Exception("NoSuchKey")
    with patch("ingestion.feature_flag_manager.boto3.client", return_value=mock_client):
        result = load_feature_flags("test-bucket")
    assert result == DEFAULT_FLAGS


def test_is_enabled_true():
    flags = {**DEFAULT_FLAGS, "enable_gpt_insights": True}
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": _make_s3_body(flags)}
    with patch("ingestion.feature_flag_manager.boto3.client", return_value=mock_client):
        result = is_enabled("enable_gpt_insights", "test-bucket")
    assert result is True


def test_enable_flag_success():
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": _make_s3_body(dict(DEFAULT_FLAGS))}
    mock_client.put_object.return_value = {}
    with patch("ingestion.feature_flag_manager.boto3.client", return_value=mock_client):
        result = enable_flag("enable_kafka_streaming", "test-bucket")
    assert result is True


def test_run_flag_audit_structure():
    sample = dict(DEFAULT_FLAGS)
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": _make_s3_body(sample)}
    with patch("ingestion.feature_flag_manager.boto3.client", return_value=mock_client):
        result = run_flag_audit("test-bucket")
    assert "total" in result
    assert "enabled" in result
    assert "disabled" in result
    assert isinstance(result["total"], int)
    assert isinstance(result["enabled"], int)
    assert isinstance(result["disabled"], int)
