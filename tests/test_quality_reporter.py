from unittest.mock import MagicMock, patch

from ingestion.quality_reporter import (
    calculate_quality_score,
    check_quality_sla,
    generate_quality_report,
)


def _make_report(ticker: str, passed: bool, failed_check: str = None) -> dict:
    checks = {"row_count": True, "no_nulls": True, "price_positive": True}
    if failed_check:
        checks[failed_check] = False
    return {"ticker": ticker, "passed": passed, "checks": checks}


def test_calculate_quality_score_all_pass():
    reports = [_make_report(t, passed=True) for t in ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]]
    result = calculate_quality_score(reports)
    assert result["quality_score_pct"] == 100.0
    assert result["passed_tickers"] == 5
    assert result["failed_tickers"] == 0


def test_calculate_quality_score_some_fail():
    reports = [
        _make_report("AAPL", passed=True),
        _make_report("MSFT", passed=True),
        _make_report("GOOGL", passed=True),
        _make_report("AMZN", passed=False, failed_check="price_positive"),
        _make_report("TSLA", passed=False, failed_check="price_positive"),
    ]
    result = calculate_quality_score(reports)
    assert result["quality_score_pct"] == 60.0
    assert result["failed_tickers"] == 2
    assert "price_positive" in result["failed_checks"]
    assert result["most_common_failure"] == "price_positive"


def test_check_quality_sla_passes():
    report = {"quality_score_pct": 90.0}
    assert check_quality_sla(report, threshold=80.0) is True


def test_check_quality_sla_fails():
    report = {"quality_score_pct": 70.0}
    assert check_quality_sla(report, threshold=80.0) is False


def test_generate_quality_report_saves_to_s3():
    sample_reports = [_make_report("AAPL", passed=True)]
    with patch("ingestion.quality_reporter.load_validation_reports", return_value=sample_reports):
        with patch("ingestion.quality_reporter.boto3") as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.client.return_value = mock_s3
            result = generate_quality_report("test-bucket", "2026/05/27")
    mock_s3.put_object.assert_called_once()
    assert result["quality_score_pct"] == 100.0
