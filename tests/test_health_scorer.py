from unittest.mock import patch

from ingestion.health_scorer import (
    calculate_overall_portfolio_score,
    score_documentation,
    score_test_coverage,
)


def test_score_test_coverage_perfect():
    score = score_test_coverage(test_count=160, module_count=20)
    assert score >= 100.0


def test_score_test_coverage_low():
    score = score_test_coverage(test_count=10, module_count=20)
    assert score < 50.0


def test_score_documentation_full():
    all_docs = [
        "README.md",
        "docs/pipeline-overview.md",
        "docs/data-dictionary.md",
        "docs/adr/README.md",
    ]
    score = score_documentation(all_docs)
    assert score == 100.0


def test_score_documentation_partial():
    partial_docs = ["README.md", "docs/pipeline-overview.md"]
    with patch("ingestion.health_scorer.os.path.exists", return_value=False):
        score = score_documentation(partial_docs)
    assert score == 50.0


def test_calculate_overall_score_grade_a():
    result = calculate_overall_portfolio_score(
        data_health=95.0,
        test_coverage=95.0,
        ci_health=95.0,
        documentation=95.0,
    )
    assert result["grade"] == "A"
    assert result["overall_score"] >= 90.0
    assert "breakdown" in result
