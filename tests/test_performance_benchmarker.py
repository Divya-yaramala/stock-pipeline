"""Tests for ingestion/performance_benchmarker.py."""

import time
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from ingestion.performance_benchmarker import (
    benchmark_function,
    benchmark_s3_operations,
    compare_benchmarks,
)


def test_benchmark_function_structure() -> None:
    result = benchmark_function(lambda: None, runs=5)
    assert "avg_ms" in result
    assert "min_ms" in result
    assert "max_ms" in result
    assert "p95_ms" in result


def test_benchmark_function_correct_runs() -> None:
    result = benchmark_function(lambda: time.sleep(0.001), runs=5)
    assert isinstance(result["avg_ms"], float)
    assert result["avg_ms"] >= 0.0
    assert result["min_ms"] <= result["avg_ms"] <= result["max_ms"]


def test_benchmark_s3_operations_structure() -> None:
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    body_mock = MagicMock()
    body_mock.read.return_value = b"{}"
    mock_client.get_object.return_value = {"Body": body_mock}
    mock_client.list_objects_v2.return_value = {"Contents": []}

    with patch("ingestion.performance_benchmarker.boto3.client", return_value=mock_client):
        result = benchmark_s3_operations("bucket")

    assert "put_avg_ms" in result
    assert "get_avg_ms" in result
    assert "list_avg_ms" in result
    assert result["runs"] == 5


def test_compare_benchmarks_regression() -> None:
    baseline: Dict[str, Any] = {"avg_ms": 100.0}
    current: Dict[str, Any] = {"avg_ms": 160.0}
    result = compare_benchmarks(baseline, current)
    assert len(result["regressions"]) > 0
    assert result["regressions"][0]["metric"] == "avg_ms"


def test_compare_benchmarks_improvement() -> None:
    baseline: Dict[str, Any] = {"avg_ms": 100.0}
    current: Dict[str, Any] = {"avg_ms": 65.0}
    result = compare_benchmarks(baseline, current)
    assert len(result["improvements"]) > 0
    assert result["improvements"][0]["metric"] == "avg_ms"
