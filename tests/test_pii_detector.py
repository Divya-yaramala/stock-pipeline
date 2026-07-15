from ingestion.pii_detector import mask_pii, scan_for_pii


def test_scan_for_pii_email_found():
    data = {"contact": "user@example.com", "ticker": "AAPL"}
    result = scan_for_pii(data)
    assert result["pii_found"] is True


def test_scan_for_pii_clean():
    data = {"ticker": "AAPL", "close_price": 185.0, "volume": 1000000}
    result = scan_for_pii(data)
    assert result["pii_found"] is False


def test_mask_pii_email():
    data = {"contact": "user@example.com", "ticker": "AAPL"}
    result = mask_pii(data)
    assert result["contact"] != "user@example.com"


def test_scan_for_pii_risk_level_high():
    data = {"note": "123-45-6789"}
    result = scan_for_pii(data)
    assert result["risk_level"] == "high"


def test_mask_pii_preserves_non_pii():
    data = {"contact": "user@example.com", "ticker": "AAPL", "close_price": 185.0}
    result = mask_pii(data)
    assert result["ticker"] == "AAPL"
    assert result["close_price"] == 185.0
