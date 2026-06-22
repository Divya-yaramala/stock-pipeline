from unittest.mock import MagicMock, patch

from ingestion.quality_scorer import (
    calculate_dq_score,
    score_completeness,
    score_timeliness,
)


def test_calculate_dq_score_structure():
    with (
        patch("ingestion.quality_scorer.score_completeness", return_value=90.0),
        patch("ingestion.quality_scorer.score_accuracy", return_value=90.0),
        patch("ingestion.quality_scorer.score_consistency", return_value=90.0),
        patch("ingestion.quality_scorer.score_timeliness", return_value=90.0),
        patch("ingestion.quality_scorer.score_validity", return_value=90.0),
    ):
        result = calculate_dq_score("AAPL", "test-bucket", "2026-06-22")
    assert "overall_score" in result
    assert "grade" in result
    assert "dimensions" in result
    assert result["ticker"] == "AAPL"


def test_grade_a_above_90():
    with (
        patch("ingestion.quality_scorer.score_completeness", return_value=95.0),
        patch("ingestion.quality_scorer.score_accuracy", return_value=95.0),
        patch("ingestion.quality_scorer.score_consistency", return_value=95.0),
        patch("ingestion.quality_scorer.score_timeliness", return_value=95.0),
        patch("ingestion.quality_scorer.score_validity", return_value=95.0),
    ):
        result = calculate_dq_score("AAPL", "test-bucket", "2026-06-22")
    assert result["grade"] == "A"
    assert result["overall_score"] >= 90.0


def test_grade_f_below_60():
    with (
        patch("ingestion.quality_scorer.score_completeness", return_value=55.0),
        patch("ingestion.quality_scorer.score_accuracy", return_value=55.0),
        patch("ingestion.quality_scorer.score_consistency", return_value=55.0),
        patch("ingestion.quality_scorer.score_timeliness", return_value=55.0),
        patch("ingestion.quality_scorer.score_validity", return_value=55.0),
    ):
        result = calculate_dq_score("AAPL", "test-bucket", "2026-06-22")
    assert result["grade"] == "F"
    assert result["overall_score"] < 60.0


def test_score_completeness_full():
    mock_s3 = MagicMock()
    mock_s3.head_object.return_value = {}
    with patch("ingestion.quality_scorer.boto3.client", return_value=mock_s3):
        result = score_completeness("test-bucket", "AAPL", "2026-06-22")
    assert result == 100.0


def test_score_timeliness_fresh():
    from datetime import datetime, timedelta, timezone

    mock_s3 = MagicMock()
    mock_s3.head_object.return_value = {
        "LastModified": datetime.now(tz=timezone.utc) - timedelta(hours=1)
    }
    with patch("ingestion.quality_scorer.boto3.client", return_value=mock_s3):
        result = score_timeliness("test-bucket", "AAPL")
    assert result == 100.0
