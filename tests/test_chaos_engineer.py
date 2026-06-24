import json
import os
from unittest.mock import MagicMock, patch

from ingestion.chaos_engineer import (
    inject_data_corruption,
    inject_partial_failure,
    run_chaos_report,
    save_chaos_event,
    should_inject_chaos,
)


def test_should_inject_chaos_disabled():
    env = {k: v for k, v in os.environ.items() if k != "CHAOS_ENABLED"}
    with patch.dict(os.environ, env, clear=True):
        for _ in range(20):
            assert should_inject_chaos("C001") is False


def test_inject_data_corruption_changes_data():
    data = {"price": 100.0, "volume": 5000, "ticker": "AAPL"}
    corrupted = inject_data_corruption(data)
    assert corrupted != data or any(v != data[k] for k, v in corrupted.items())


def test_inject_partial_failure_reduces_list():
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    result = inject_partial_failure(tickers)
    assert len(result) < len(tickers)


def test_save_chaos_event_success():
    mock_s3 = MagicMock()
    with patch("ingestion.chaos_engineer.boto3.client", return_value=mock_s3):
        mock_s3.put_object.return_value = {}
        result = save_chaos_event("C001", {"detail": "test"}, "test-bucket")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_run_chaos_report_structure():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {"Contents": [{"Key": "chaos/2026/06/24/C001_123.json"}]}
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=lambda: json.dumps({"scenario_id": "C001"}).encode())
    }
    with patch("ingestion.chaos_engineer.boto3.client", return_value=mock_s3):
        result = run_chaos_report("test-bucket", "2026-06-24")
    assert "total_events" in result
    assert "by_scenario" in result
    assert result["total_events"] == 1
