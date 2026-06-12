import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

from ingestion.data_observatory import (
    calculate_health_score,
    check_data_completeness,
    check_data_freshness,
)


def test_check_data_freshness_fresh():
    recent = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    payload = json.dumps({"timestamp": recent}).encode()
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": BytesIO(payload)}

    with patch("ingestion.data_observatory.boto3.client", return_value=mock_s3):
        result = check_data_freshness("test-bucket", "AAPL")

    assert result["is_fresh"] is True
    assert result["hours_since_update"] < 25.0
    assert result["ticker"] == "AAPL"


def test_check_data_freshness_stale():
    old = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    payload = json.dumps({"timestamp": old}).encode()
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": BytesIO(payload)}

    with patch("ingestion.data_observatory.boto3.client", return_value=mock_s3):
        result = check_data_freshness("test-bucket", "AAPL")

    assert result["is_fresh"] is False
    assert result["hours_since_update"] >= 25.0


def test_check_data_completeness_full():
    mock_s3 = MagicMock()
    mock_s3.head_object.return_value = {}

    with patch("ingestion.data_observatory.boto3.client", return_value=mock_s3):
        result = check_data_completeness("test-bucket", "AAPL", "2026-06-11")

    assert result["completeness_pct"] == 100.0
    assert result["missing"] == []
    assert result["ticker"] == "AAPL"


def test_check_data_completeness_partial():
    call_count = {"n": 0}

    def head_side_effect(**kwargs):
        call_count["n"] += 1
        if call_count["n"] > 3:
            raise Exception("Not found")

    mock_s3 = MagicMock()
    mock_s3.head_object.side_effect = head_side_effect

    with patch("ingestion.data_observatory.boto3.client", return_value=mock_s3):
        result = check_data_completeness("test-bucket", "AAPL", "2026-06-11")

    assert result["completeness_pct"] == 60.0
    assert len(result["missing"]) == 2


def test_calculate_health_score_perfect():
    freshness = {
        "ticker": "AAPL",
        "is_fresh": True,
        "hours_since_update": 1.0,
        "last_updated": "2026-06-11",
    }
    completeness = {
        "ticker": "AAPL",
        "date": "2026-06-11",
        "completeness_pct": 100.0,
        "missing": [],
    }
    consistency = {"ticker": "AAPL", "is_consistent": True, "issues": []}

    score = calculate_health_score(freshness, completeness, consistency)

    assert score == 100.0
