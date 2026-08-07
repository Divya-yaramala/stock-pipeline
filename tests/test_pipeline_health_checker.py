import os
from unittest.mock import MagicMock, patch

from ingestion.pipeline_health_checker import (
    check_dependencies_installed,
    check_environment_variables,
    check_test_suite_health,
    run_full_health_check,
)


def test_check_dependencies_installed_structure():
    result = check_dependencies_installed()
    assert "total" in result
    assert "installed" in result


def test_check_environment_variables_structure():
    os.environ["AWS_BUCKET_NAME"] = "test-bucket"
    os.environ["AWS_ACCESS_KEY_ID"] = "fake-key"
    result = check_environment_variables()
    assert "required_present" in result
    assert result["required_present"] >= 2


def test_run_full_health_check_structure():
    with patch("ingestion.pipeline_health_checker.check_all_modules_importable") as mock_mod, patch(
        "ingestion.pipeline_health_checker.check_test_suite_health"
    ) as mock_tests, patch(
        "ingestion.pipeline_health_checker.check_dependencies_installed"
    ) as mock_deps, patch(
        "ingestion.pipeline_health_checker.check_environment_variables"
    ) as mock_env:
        mock_mod.return_value = {"total": 15, "importable": 15, "failed": []}
        mock_tests.return_value = {"test_files": 37, "test_count": 712, "status": "ok"}
        mock_deps.return_value = {"total": 30, "installed": 30, "missing": []}
        mock_env.return_value = {"required_present": 7, "required_total": 7, "missing": []}
        result = run_full_health_check()
    assert "overall_score" in result
    assert "grade" in result


def test_run_full_health_check_grade_a():
    with patch("ingestion.pipeline_health_checker.check_all_modules_importable") as mock_mod, patch(
        "ingestion.pipeline_health_checker.check_test_suite_health"
    ) as mock_tests, patch(
        "ingestion.pipeline_health_checker.check_dependencies_installed"
    ) as mock_deps, patch(
        "ingestion.pipeline_health_checker.check_environment_variables"
    ) as mock_env:
        mock_mod.return_value = {"total": 15, "importable": 15, "failed": []}
        mock_tests.return_value = {"test_files": 37, "test_count": 712, "status": "ok"}
        mock_deps.return_value = {"total": 30, "installed": 30, "missing": []}
        mock_env.return_value = {"required_present": 7, "required_total": 7, "missing": []}
        result = run_full_health_check()
    assert result["grade"] == "A"


def test_check_test_suite_health_structure():
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "tests/test_fetch_stocks.py::test_foo\ntests/test_anomaly.py::test_bar\n"
    mock_proc.stderr = ""
    with patch("ingestion.pipeline_health_checker.subprocess.run", return_value=mock_proc):
        result = check_test_suite_health()
    assert "status" in result
