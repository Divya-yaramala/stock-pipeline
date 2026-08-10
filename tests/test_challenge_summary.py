from unittest.mock import MagicMock, patch

from ingestion.challenge_summary import (
    generate_completion_certificate,
    get_final_stats,
    run_challenge_summary,
)


def test_get_final_stats_structure():
    with patch("boto3.client"):
        stats = get_final_stats("test-bucket")
    assert isinstance(stats, dict)
    assert "total_modules" in stats


def test_get_final_stats_values():
    with patch("boto3.client"):
        stats = get_final_stats("test-bucket")
    assert stats["total_days"] == 90
    assert stats["total_apis"] == 3


def test_generate_completion_certificate_structure():
    with patch("boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        cert = generate_completion_certificate("test-bucket")
    assert isinstance(cert, dict)
    assert "certificate_id" in cert


def test_generate_completion_certificate_achievements():
    with patch("boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        cert = generate_completion_certificate("test-bucket")
    assert isinstance(cert["achievements"], list)
    assert len(cert["achievements"]) > 0


def test_run_challenge_summary_structure():
    with patch("boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        result = run_challenge_summary("test-bucket")
    assert isinstance(result, dict)
    assert "stats" in result
    assert "certificate" in result
