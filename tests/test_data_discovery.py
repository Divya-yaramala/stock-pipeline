import json
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from ingestion.data_discovery import (
    discover_s3_datasets,
    get_dataset_stats,
    profile_dataset,
    run_data_discovery,
    search_datasets,
)


def _make_s3_mock(prefixes: List[str], contents: List[Dict[str, Any]]) -> MagicMock:
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "CommonPrefixes": [{"Prefix": p} for p in prefixes],
        "Contents": contents,
    }
    paginator = MagicMock()
    paginator.paginate.return_value = iter(
        [{"Contents": contents}] if contents else [{"Contents": []}]
    )
    mock_s3.get_paginator.return_value = paginator
    return mock_s3


def test_discover_s3_datasets_returns_list():
    mock_s3 = _make_s3_mock(["raw/", "processed/"], [])
    with patch("ingestion.data_discovery.boto3.client", return_value=mock_s3):
        result = discover_s3_datasets("test-bucket")
    assert isinstance(result, list)
    assert len(result) == 2


def test_search_datasets_filters_correctly():
    mock_s3 = _make_s3_mock(["raw/stocks/", "anomalies/", "processed/"], [])
    with patch("ingestion.data_discovery.boto3.client", return_value=mock_s3):
        result = search_datasets("test-bucket", "anomalies")
    assert len(result) == 1
    assert result[0]["prefix"] == "anomalies/"


def test_get_dataset_stats_structure():
    contents = [{"Key": "raw/file.json", "Size": 2048, "LastModified": "2026-07-10"}]
    mock_s3 = _make_s3_mock([], contents)
    with patch("ingestion.data_discovery.boto3.client", return_value=mock_s3):
        result = get_dataset_stats("test-bucket", "raw/")
    assert "record_count" in result
    assert "date_range" in result
    assert "size_mb" in result
    assert "avg_record_size_kb" in result


def test_profile_dataset_structure():
    sample = json.dumps({"ticker": "AAPL", "price": 150.0, "volume": None}).encode("utf-8")
    mock_body = MagicMock()
    mock_body.read.return_value = sample
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {"Contents": [{"Key": "raw/stocks/AAPL.json"}]}
    mock_s3.get_object.return_value = {"Body": mock_body}
    with patch("ingestion.data_discovery.boto3.client", return_value=mock_s3):
        result = profile_dataset("test-bucket", "raw/stocks/")
    assert "schema" in result
    assert "null_counts" in result
    assert "records_sampled" in result


def test_run_data_discovery_structure():
    mock_s3 = _make_s3_mock(
        ["raw/"], [{"Key": "raw/f.json", "Size": 512, "LastModified": "2026-07-10"}]
    )
    mock_s3.list_objects_v2.side_effect = [
        {"CommonPrefixes": [{"Prefix": "raw/"}], "Contents": []},
        {"Contents": [{"Key": "raw/f.json"}]},
    ]
    mock_s3.get_object.side_effect = Exception("no file")
    with patch("ingestion.data_discovery.boto3.client", return_value=mock_s3):
        result = run_data_discovery("test-bucket")
    assert "datasets" in result
    assert "total_datasets" in result
