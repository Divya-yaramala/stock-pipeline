import json
from unittest.mock import MagicMock, patch

import pytest

from ingestion.event_bus import (
    get_event_summary,
    get_events,
    publish_event,
    publish_pipeline_completed,
)


def _make_s3_body(data: dict) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return body


def test_publish_event_success():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.event_bus.boto3.client", return_value=mock_client):
        result = publish_event(
            "pipeline_completed",
            {"ticker": "AAPL"},
            "test_source",
            "test-bucket",
        )
    assert isinstance(result, str)
    assert len(result) > 0
    mock_client.put_object.assert_called_once()


def test_publish_event_invalid_type():
    mock_client = MagicMock()
    with patch("ingestion.event_bus.boto3.client", return_value=mock_client):
        with pytest.raises(ValueError):
            publish_event(
                "not_a_real_event",
                {"ticker": "AAPL"},
                "test_source",
                "test-bucket",
            )


def test_get_events_returns_list():
    event = {
        "event_id": "abc-123",
        "event_type": "pipeline_completed",
        "payload": {},
        "source": "pipeline",
        "published_at": "2026-07-13T00:00:00",
    }
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [{"Key": "events/2026/07/13/pipeline_completed/abc-123.json"}]
    }
    mock_client.get_object.return_value = {"Body": _make_s3_body(event)}
    with patch("ingestion.event_bus.boto3.client", return_value=mock_client):
        result = get_events("pipeline_completed", "test-bucket", "2026/07/13")
    assert isinstance(result, list)
    assert len(result) == 1


def test_get_event_summary_structure():
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {"Contents": []}
    with patch("ingestion.event_bus.boto3.client", return_value=mock_client):
        result = get_event_summary("test-bucket", "2026/07/13")
    assert isinstance(result, dict)
    assert "total" in result
    assert "by_type" in result
    assert "date" in result
    assert isinstance(result["total"], int)
    assert isinstance(result["by_type"], dict)


def test_publish_pipeline_completed_success():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.event_bus.boto3.client", return_value=mock_client):
        result = publish_pipeline_completed("AAPL", 45.5, "test-bucket")
    assert isinstance(result, str)
    assert len(result) > 0
