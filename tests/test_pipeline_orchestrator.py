from unittest.mock import MagicMock, patch

from ingestion.pipeline_orchestrator import (
    get_ready_steps,
    get_step_status,
    reset_failed_steps,
    run_orchestration_check,
    update_step_status,
)


def test_get_step_status_pending():
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = Exception("NoSuchKey")
    with patch("ingestion.pipeline_orchestrator.boto3.client", return_value=mock_s3):
        result = get_step_status("S001", "test-bucket", "2026-06-21")
    assert result == "pending"


def test_update_step_status_success():
    mock_s3 = MagicMock()
    with patch("ingestion.pipeline_orchestrator.boto3.client", return_value=mock_s3):
        result = update_step_status("S001", "success", "test-bucket", "2026-06-21")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_get_ready_steps_no_deps():
    def fake_status(step_id, bucket, date):
        return "pending"

    with patch("ingestion.pipeline_orchestrator.get_step_status", side_effect=fake_status):
        result = get_ready_steps("test-bucket", "2026-06-21")

    step_ids = [s["step_id"] for s in result]
    assert "S001" in step_ids
    for step in result:
        assert step["depends_on"] == []


def test_run_orchestration_check_structure():
    def fake_status(step_id, bucket, date):
        return "success"

    with patch("ingestion.pipeline_orchestrator.get_step_status", side_effect=fake_status):
        result = run_orchestration_check("test-bucket", "2026-06-21")

    assert "total" in result
    assert "success" in result
    assert "failed" in result
    assert result["total"] == 10
    assert result["success"] == 10


def test_reset_failed_steps_count():
    failed_steps = {"S003", "S007"}

    def fake_status(step_id, bucket, date):
        return "failed" if step_id in failed_steps else "success"

    with patch("ingestion.pipeline_orchestrator.get_step_status", side_effect=fake_status), patch(
        "ingestion.pipeline_orchestrator.update_step_status", return_value=True
    ):
        result = reset_failed_steps("test-bucket", "2026-06-21")

    assert result == 2
