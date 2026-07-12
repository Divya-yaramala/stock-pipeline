import json
from unittest.mock import MagicMock, patch

from ingestion.experiment_manager import (
    analyze_experiment,
    conclude_experiment,
    create_experiment,
    get_variant,
)


def _make_s3_body(data: dict) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return body


def test_create_experiment_success():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.experiment_manager.boto3.client", return_value=mock_client):
        exp_id = create_experiment(
            name="test_exp",
            description="A test experiment",
            variants=["control", "treatment"],
            bucket="test-bucket",
        )
    assert isinstance(exp_id, str)
    assert len(exp_id) > 0


def test_get_variant_consistent():
    config = {
        "variants": ["control", "treatment"],
        "traffic_split": {"control": 0.5, "treatment": 0.5},
    }
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": _make_s3_body(config)}
    with patch("ingestion.experiment_manager.boto3.client", return_value=mock_client):
        v1 = get_variant("exp123", "AAPL", "test-bucket")
    mock_client2 = MagicMock()
    mock_client2.get_object.return_value = {"Body": _make_s3_body(config)}
    with patch("ingestion.experiment_manager.boto3.client", return_value=mock_client2):
        v2 = get_variant("exp123", "AAPL", "test-bucket")
    assert v1 == v2


def test_get_variant_valid_output():
    config = {
        "variants": ["control", "treatment"],
        "traffic_split": {"control": 0.5, "treatment": 0.5},
    }
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": _make_s3_body(config)}
    with patch("ingestion.experiment_manager.boto3.client", return_value=mock_client):
        variant = get_variant("exp123", "MSFT", "test-bucket")
    assert variant in ["control", "treatment"]


def test_analyze_experiment_structure():
    outcome_a = {
        "variant": "control",
        "ticker": "AAPL",
        "metric_name": "accuracy",
        "metric_value": 0.82,
    }
    outcome_b = {
        "variant": "treatment",
        "ticker": "MSFT",
        "metric_name": "accuracy",
        "metric_value": 0.91,
    }
    mock_client = MagicMock()
    page = {
        "Contents": [
            {"Key": "experiments/exp1/outcomes/AAPL_ts.json"},
            {"Key": "experiments/exp1/outcomes/MSFT_ts.json"},
        ]
    }
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [page]
    mock_client.get_paginator.return_value = mock_paginator
    mock_client.get_object.side_effect = [
        {"Body": _make_s3_body(outcome_a)},
        {"Body": _make_s3_body(outcome_b)},
    ]
    with patch("ingestion.experiment_manager.boto3.client", return_value=mock_client):
        result = analyze_experiment("exp1", "test-bucket")
    assert "winner" in result
    assert "by_variant" in result
    assert "sample_count" in result
    assert result["sample_count"] == 2


def test_conclude_experiment_structure():
    config = {
        "experiment_id": "exp1",
        "name": "test",
        "description": "desc",
        "variants": ["control", "treatment"],
        "traffic_split": {"control": 0.5, "treatment": 0.5},
        "status": "running",
        "created_at": "2026-07-12T00:00:00",
    }
    outcome = {
        "variant": "control",
        "ticker": "AAPL",
        "metric_name": "accuracy",
        "metric_value": 0.88,
    }
    mock_client = MagicMock()
    page = {"Contents": [{"Key": "experiments/exp1/outcomes/AAPL_ts.json"}]}
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [page]
    mock_client.get_paginator.return_value = mock_paginator
    mock_client.get_object.side_effect = [
        {"Body": _make_s3_body(outcome)},
        {"Body": _make_s3_body(config)},
    ]
    mock_client.put_object.return_value = {}
    with patch("ingestion.experiment_manager.boto3.client", return_value=mock_client):
        result = conclude_experiment("exp1", "test-bucket")
    assert "status" in result
    assert result["status"] == "concluded"
