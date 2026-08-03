from ingestion.pipeline_validator import (
    run_validation_suite,
    validate_business_rules,
    validate_schema,
)


def test_validate_schema_passes():
    data = {
        "ticker": "AAPL",
        "trade_date": "2026-07-29",
        "open_price": 185.0,
        "high_price": 190.0,
        "low_price": 183.0,
        "close_price": 188.0,
        "volume": 1000000,
    }
    required = [
        "ticker",
        "trade_date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
    ]
    result = validate_schema(data, required)
    assert result["passed"] is True
    assert result["missing_fields"] == []


def test_validate_schema_fails():
    data = {
        "ticker": "AAPL",
        "trade_date": "2026-07-29",
        "open_price": 185.0,
    }
    required = [
        "ticker",
        "trade_date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
    ]
    result = validate_schema(data, required)
    assert result["passed"] is False
    assert "high_price" in result["missing_fields"]


def test_validate_business_rules_passes():
    data = {
        "high_price": 190.0,
        "low_price": 183.0,
        "close_price": 188.0,
        "open_price": 185.0,
        "volume": 1000000,
    }
    result = validate_business_rules(data)
    assert result["passed"] is True
    assert result["violations"] == []


def test_validate_business_rules_fails():
    data = {
        "high_price": 180.0,
        "low_price": 190.0,
        "close_price": 185.0,
        "open_price": 185.0,
        "volume": 1000000,
    }
    result = validate_business_rules(data)
    assert result["passed"] is False
    assert len(result["violations"]) > 0


def test_run_validation_suite_structure():
    records = [
        {
            "ticker": "AAPL",
            "trade_date": "2026-07-29",
            "open_price": 185.0,
            "high_price": 190.0,
            "low_price": 183.0,
            "close_price": 188.0,
            "volume": 1000000,
        }
    ]
    result = run_validation_suite(records, "AAPL")
    assert "pass_rate_pct" in result
    assert result["total_rules"] == 8
    assert "passed" in result
    assert "failed" in result
