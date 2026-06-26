import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from ingestion.secrets_manager import (
    audit_secret_access,
    decrypt_value,
    encrypt_value,
    get_secret,
    list_secrets,
    store_secret,
)


def test_encrypt_decrypt_roundtrip():
    original = "my-super-secret-password"
    key = "test-key"
    encrypted = encrypt_value(original, key)
    decrypted = decrypt_value(encrypted, key)
    assert decrypted == original


def test_store_secret_success():
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {}
    with patch("ingestion.secrets_manager.boto3.client", return_value=mock_s3):
        result = store_secret("my_api_key", "secret123", "test-bucket")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_get_secret_success():
    original = "secret-value-xyz"
    from ingestion.secrets_manager import ENCRYPTION_KEY, encrypt_value

    encrypted = encrypt_value(original, ENCRYPTION_KEY)
    payload = json.dumps({"secret_name": "my_key", "encrypted_value": encrypted}).encode()
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": BytesIO(payload)}
    with patch("ingestion.secrets_manager.boto3.client", return_value=mock_s3):
        result = get_secret("my_key", "test-bucket")
    assert result == original


def test_list_secrets_returns_names_only():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "secrets/api_key.json"},
            {"Key": "secrets/db_password.json"},
            {"Key": "secrets/audit/2026/06/25/123456.json"},
        ]
    }
    with patch("ingestion.secrets_manager.boto3.client", return_value=mock_s3):
        result = list_secrets("test-bucket")
    assert isinstance(result, list)
    assert all(isinstance(name, str) for name in result)
    assert "api_key" in result
    assert "db_password" in result
    assert len(result) == 2


def test_audit_secret_access_success():
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {}
    with patch("ingestion.secrets_manager.boto3.client", return_value=mock_s3):
        result = audit_secret_access("my_api_key", "read", "test-bucket")
    assert result is True
    mock_s3.put_object.assert_called_once()
