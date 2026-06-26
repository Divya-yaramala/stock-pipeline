import os
import tempfile
from unittest.mock import MagicMock, patch

from ingestion.security_scanner import (
    generate_security_report,
    run_security_scan,
    scan_directory,
    scan_for_hardcoded_secrets,
)


def test_scan_for_hardcoded_secrets_found():
    content = 'aws_key = "AKIAIOSFODNN7EXAMPLE"\n'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        findings = scan_for_hardcoded_secrets(path)
        assert len(findings) > 0
        assert findings[0]["file"] == path
    finally:
        os.unlink(path)


def test_scan_for_hardcoded_secrets_clean():
    content = "import os\n\ndef get_data():\n    return []\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        findings = scan_for_hardcoded_secrets(path)
        assert findings == []
    finally:
        os.unlink(path)


def test_scan_directory_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        clean_file = os.path.join(tmpdir, "clean.py")
        with open(clean_file, "w") as f:
            f.write("x = 1\n")
        result = scan_directory(tmpdir)
    assert "total_files" in result
    assert "files_with_issues" in result
    assert "findings" in result
    assert result["total_files"] >= 1


def test_generate_security_report_success():
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {}
    scan_results = {"total_files": 5, "files_with_issues": 1, "findings": [{"line": 3}]}
    with patch("ingestion.security_scanner.boto3.client", return_value=mock_s3):
        result = generate_security_report(scan_results, "test-bucket")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_run_security_scan_structure():
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {}
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = os.path.join(tmpdir, "sample.py")
        with open(py_file, "w") as f:
            f.write("x = 1\n")
        with patch("ingestion.security_scanner.boto3.client", return_value=mock_s3):
            result = run_security_scan(tmpdir, "test-bucket")
    assert "findings" in result
    assert isinstance(result["findings"], list)
