from unittest.mock import MagicMock, patch

from ingestion.distributed_tracer import (
    analyze_trace,
    end_span,
    run_pipeline_with_tracing,
    start_span,
    start_trace,
)


def test_start_trace_returns_id():
    trace_id = start_trace("test_trace", "AAPL")
    assert isinstance(trace_id, str)


def test_start_span_returns_id():
    trace_id = start_trace("test_trace", "MSFT")
    span_id = start_span(trace_id, "fetch_data")
    assert isinstance(span_id, str)


def test_end_span_success():
    trace_id = start_trace("test_trace", "GOOGL")
    span_id = start_span(trace_id, "validate")
    with patch("ingestion.distributed_tracer.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        result = end_span(trace_id, span_id, "ok", "test-bucket")
    assert result is True


def test_analyze_trace_structure():
    trace = {
        "trace_id": "abc123",
        "spans": [
            {"span_id": "s1", "span_name": "fetch_data", "duration_ms": 200.0, "status": "ok"},
            {"span_id": "s2", "span_name": "validate", "duration_ms": 50.0, "status": "error"},
        ],
        "total_duration_ms": 250.0,
    }
    result = analyze_trace(trace)
    assert "slowest_span" in result


def test_run_pipeline_with_tracing_returns_id():
    with patch("ingestion.distributed_tracer.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        result = run_pipeline_with_tracing("AAPL", "test-bucket")
    assert isinstance(result, str)
