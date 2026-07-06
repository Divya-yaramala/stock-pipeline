from unittest.mock import MagicMock, patch

from ingestion.ab_tester import analyze_ab_results, assign_model, create_ab_experiment


def test_create_ab_experiment_success():
    mock_s3 = MagicMock()
    with patch("ingestion.ab_tester.boto3.client", return_value=mock_s3):
        result = create_ab_experiment("test_exp", "prophet", "ensemble", 0.5, "test-bucket")
    assert isinstance(result, str)
    assert len(result) > 0


def test_assign_model_consistent():
    result1 = assign_model("exp_123", "AAPL", "test-bucket")
    result2 = assign_model("exp_123", "AAPL", "test-bucket")
    assert result1 == result2


def test_assign_model_valid_output():
    result = assign_model("exp_123", "MSFT", "test-bucket")
    assert result in ("model_a", "model_b")


def test_analyze_ab_results_structure():
    mock_s3 = MagicMock()
    mock_page = {
        "Contents": [
            {"Key": "models/experiments/exp_123/results/AAPL_1.json"},
            {"Key": "models/experiments/exp_123/results/MSFT_2.json"},
        ]
    }
    import json

    result_a = json.dumps({"model_assigned": "model_a", "error": 5.0})
    result_b = json.dumps({"model_assigned": "model_b", "error": 7.0})

    mock_s3.get_paginator.return_value.paginate.return_value = [mock_page]
    mock_s3.get_object.side_effect = [
        {"Body": MagicMock(read=MagicMock(return_value=result_a.encode()))},
        {"Body": MagicMock(read=MagicMock(return_value=result_b.encode()))},
    ]
    with patch("ingestion.ab_tester.boto3.client", return_value=mock_s3):
        result = analyze_ab_results("exp_123", "test-bucket")
    assert "winner" in result


def test_analyze_ab_results_confidence_high():
    mock_s3 = MagicMock()
    import json

    contents = [{"Key": f"models/experiments/exp_456/results/AAPL_{i}.json"} for i in range(35)]
    mock_page = {"Contents": contents}

    def make_result(i: int) -> dict:
        model = "model_a" if i % 2 == 0 else "model_b"
        return {
            "Body": MagicMock(
                read=MagicMock(
                    return_value=json.dumps({"model_assigned": model, "error": 4.0}).encode()
                )
            )
        }

    mock_s3.get_paginator.return_value.paginate.return_value = [mock_page]
    mock_s3.get_object.side_effect = [make_result(i) for i in range(35)]

    with patch("ingestion.ab_tester.boto3.client", return_value=mock_s3):
        result = analyze_ab_results("exp_456", "test-bucket")
    assert result["confidence"] == "high"
