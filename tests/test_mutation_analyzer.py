import os
import tempfile

from ingestion.mutation_analyzer import (
    calculate_mutation_score,
    find_mutation_candidates,
    generate_mutation_report,
)


def test_find_mutation_candidates_returns_list():
    code = "def foo(x):\n    if x > 0:\n        return True\n    return False\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = find_mutation_candidates(tmp_path)
        assert isinstance(result, list)
        assert len(result) > 0
    finally:
        os.unlink(tmp_path)


def test_calculate_mutation_score_100():
    score = calculate_mutation_score(100, 100)
    assert score == 100.0


def test_calculate_mutation_score_0():
    score = calculate_mutation_score(100, 0)
    assert score == 0.0


def test_generate_mutation_report_structure():
    code = "def foo(x):\n    if x > 0:\n        return True\n    return False\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = generate_mutation_report(tmp_path, "tests/test_foo.py")
        assert isinstance(result, dict)
        assert "candidates" in result
    finally:
        os.unlink(tmp_path)


def test_find_mutation_candidates_operators():
    code = "def check(x, y):\n    if x > y:\n        return x < y\n    return x == y\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = find_mutation_candidates(tmp_path)
        types = [c["type"] for c in result]
        assert "comparison" in types
    finally:
        os.unlink(tmp_path)
