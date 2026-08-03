from unittest.mock import MagicMock, patch

from ingestion.workflow_automation_engine import (
    calculate_workflow_reliability,
    register_workflow,
    run_automation_check,
    trigger_workflow,
    update_workflow_status,
)


def test_register_workflow_success():
    workflow = {"workflow_id": "AW001", "name": "daily_refresh", "steps": ["fetch", "load"]}
    with patch("ingestion.workflow_automation_engine.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        result = register_workflow(workflow, "test-bucket")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_trigger_workflow_returns_id():
    with patch("ingestion.workflow_automation_engine.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        execution_id = trigger_workflow("AW001", "manual_trigger", "test-bucket")
    assert isinstance(execution_id, str)
    assert "AW001" in execution_id


def test_update_workflow_status_success():
    with patch("ingestion.workflow_automation_engine.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.get_object.side_effect = Exception("not found")
        result = update_workflow_status(
            "AW001_20260803_060000", "running", "validate", "test-bucket"
        )
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_calculate_workflow_reliability_structure():
    executions = [
        {
            "status": "completed",
            "started_at": "2026-08-03T06:00:00",
            "completed_at": "2026-08-03T06:05:00",
        },
        {
            "status": "completed",
            "started_at": "2026-08-02T06:00:00",
            "completed_at": "2026-08-02T06:08:00",
        },
        {"status": "failed"},
    ]
    result = calculate_workflow_reliability(executions)
    assert "success_rate_pct" in result
    assert "avg_duration_minutes" in result
    assert "failure_count" in result
    assert result["failure_count"] == 1


def test_run_automation_check_structure():
    with patch("ingestion.workflow_automation_engine.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.put_object.return_value = {}
        mock_s3.get_paginator.return_value.paginate.return_value = [{"Contents": []}]
        result = run_automation_check("test-bucket")
    assert "workflows_registered" in result
    assert result["workflows_registered"] == 5
