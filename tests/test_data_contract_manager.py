from unittest.mock import MagicMock, patch

from ingestion.data_contract_manager import (
    STOCK_PRICE_CONTRACT,
    check_contract_compatibility,
    register_contract,
    validate_against_contract,
)


def test_register_contract_success():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.data_contract_manager.boto3.client", return_value=mock_client):
        result = register_contract(STOCK_PRICE_CONTRACT, "test-bucket")
    assert result is True
    mock_client.put_object.assert_called_once()


def test_validate_against_contract_valid():
    data = {
        "ticker": "AAPL",
        "trade_date": "2026-07-14",
        "open_price": 185.0,
        "high_price": 190.0,
        "low_price": 183.0,
        "close_price": 188.0,
        "volume": 1000000,
    }
    result = validate_against_contract(data, STOCK_PRICE_CONTRACT)
    assert result["valid"] is True
    assert result["violations"] == []


def test_validate_against_contract_missing_field():
    data = {
        "trade_date": "2026-07-14",
        "open_price": 185.0,
        "high_price": 190.0,
        "low_price": 183.0,
        "close_price": 188.0,
        "volume": 1000000,
    }
    result = validate_against_contract(data, STOCK_PRICE_CONTRACT)
    assert result["valid"] is False
    assert any("ticker" in v for v in result["violations"])


def test_check_contract_compatibility_breaking():
    old_contract = {
        "contract_id": "C001",
        "schema": {
            "ticker": {"type": "string", "required": True},
            "close_price": {"type": "float", "required": True},
        },
    }
    new_contract = {
        "contract_id": "C001",
        "schema": {
            "close_price": {"type": "float", "required": True},
        },
    }
    result = check_contract_compatibility(old_contract, new_contract)
    assert result["compatible"] is False
    assert len(result["breaking_changes"]) > 0


def test_check_contract_compatibility_safe():
    old_contract = {
        "contract_id": "C001",
        "schema": {
            "ticker": {"type": "string", "required": True},
        },
    }
    new_contract = {
        "contract_id": "C001",
        "schema": {
            "ticker": {"type": "string", "required": True},
            "exchange": {"type": "string", "required": False},
        },
    }
    result = check_contract_compatibility(old_contract, new_contract)
    assert result["compatible"] is True
    assert result["breaking_changes"] == []
