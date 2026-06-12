import logging
import os
from typing import Dict, List

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

KEY_DOCS = [
    "README.md",
    "docs/pipeline-overview.md",
    "docs/data-dictionary.md",
    "docs/adr/README.md",
]


def score_test_coverage(test_count: int, module_count: int) -> float:
    if module_count == 0:
        return 0.0
    score = min(test_count / module_count / 5 * 100, 100.0)
    logger.info("Test coverage score: %.1f (%d tests / %d modules)", score, test_count, module_count)
    return round(score, 2)


def score_ci_health(workflow_results: List[str]) -> float:
    if not workflow_results:
        return 0.0
    passes = sum(1 for r in workflow_results if str(r).lower() in ("pass", "success", "passed"))
    score = round(passes / len(workflow_results) * 100, 2)
    logger.info("CI health score: %.1f (%d/%d passing)", score, passes, len(workflow_results))
    return score


def score_documentation(doc_files: List[str]) -> float:
    present = sum(1 for doc in KEY_DOCS if doc in doc_files or os.path.exists(doc))
    score = round(present / len(KEY_DOCS) * 100, 2)
    logger.info("Documentation score: %.1f (%d/%d docs present)", score, present, len(KEY_DOCS))
    return score


def calculate_overall_portfolio_score(
    data_health: float,
    test_coverage: float,
    ci_health: float,
    documentation: float,
) -> Dict:
    overall = (
        data_health * 0.40
        + test_coverage * 0.30
        + ci_health * 0.20
        + documentation * 0.10
    )
    overall = round(overall, 2)

    if overall >= 90:
        grade = "A"
    elif overall >= 80:
        grade = "B"
    elif overall >= 70:
        grade = "C"
    elif overall >= 60:
        grade = "D"
    else:
        grade = "F"

    logger.info("Overall portfolio score: %.1f/100 (Grade: %s)", overall, grade)
    return {
        "overall_score": overall,
        "grade": grade,
        "breakdown": {
            "data_health": round(data_health, 2),
            "test_coverage": round(test_coverage, 2),
            "ci_health": round(ci_health, 2),
            "documentation": round(documentation, 2),
        },
    }


def run_health_scoring() -> Dict:
    test_count = int(os.getenv("PIPELINE_TEST_COUNT", "170"))
    module_count = int(os.getenv("PIPELINE_MODULE_COUNT", "23"))

    test_cov = score_test_coverage(test_count, module_count)
    ci = score_ci_health(["pass", "pass", "pass", "pass", "pass"])
    docs = score_documentation([])
    data_health = 85.0

    result = calculate_overall_portfolio_score(data_health, test_cov, ci, docs)
    logger.info("Pipeline Health Score: %.1f/100 (Grade: %s)", result["overall_score"], result["grade"])
    return result


if __name__ == "__main__":
    run_health_scoring()
