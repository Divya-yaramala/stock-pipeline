from unittest.mock import MagicMock, patch

from ingestion.alerting_rules import (
    evaluate_all_rules,
    evaluate_rule,
    save_rule_results,
)


def test_evaluate_rule_triggered():
    rule = {"rule_id": "T001", "metric": "anomaly_rate_pct", "operator": ">", "threshold": 20.0}
    metrics = {"anomaly_rate_pct": 25.0}
    assert evaluate_rule(rule, metrics) is True


def test_evaluate_rule_not_triggered():
    rule = {"rule_id": "T001", "metric": "anomaly_rate_pct", "operator": ">", "threshold": 20.0}
    metrics = {"anomaly_rate_pct": 15.0}
    assert evaluate_rule(rule, metrics) is False


def test_evaluate_all_rules_returns_list():
    metrics = {
        "anomaly_rate_pct": 5.0,
        "quality_score_pct": 95.0,
        "sla_met_pct": 100.0,
        "error_rate_pct": 1.0,
        "prediction_accuracy_pct": 85.0,
    }
    result = evaluate_all_rules(metrics)
    assert isinstance(result, list)


def test_save_rule_results_success():
    mock_s3 = MagicMock()
    with patch("ingestion.alerting_rules.boto3.client", return_value=mock_s3):
        result = save_rule_results([], "test-bucket", "2026-06-18")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_evaluate_rule_all_operators():
    base = {"rule_id": "X", "metric": "val", "threshold": 10.0}
    assert evaluate_rule({**base, "operator": ">"}, {"val": 15.0}) is True
    assert evaluate_rule({**base, "operator": ">"}, {"val": 5.0}) is False
    assert evaluate_rule({**base, "operator": "<"}, {"val": 5.0}) is True
    assert evaluate_rule({**base, "operator": "<"}, {"val": 15.0}) is False
    assert evaluate_rule({**base, "operator": ">="}, {"val": 10.0}) is True
    assert evaluate_rule({**base, "operator": "<="}, {"val": 10.0}) is True
    assert evaluate_rule({**base, "operator": "=="}, {"val": 10.0}) is True
    assert evaluate_rule({**base, "operator": "=="}, {"val": 11.0}) is False
