import ast
import json
import logging
import os
import re
from datetime import datetime

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_mutation_candidates(file_path: str) -> list:
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    # Quick pre-scan: skip files with no Python definitions
    if not re.search(r"\bdef \b|\bclass \b", source):
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        logger.warning("Could not parse %s: %s", file_path, e)
        return []
    candidates = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for op in node.ops:
                candidates.append(
                    {"type": "comparison", "operator": type(op).__name__, "line": node.lineno}
                )
        elif isinstance(node, ast.BoolOp):
            candidates.append(
                {"type": "boolean", "operator": type(node.op).__name__, "line": node.lineno}
            )
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            candidates.append({"type": "boolean", "operator": "Not", "line": node.lineno})
        elif isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)
        ):
            candidates.append(
                {"type": "arithmetic", "operator": type(node.op).__name__, "line": node.lineno}
            )
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, bool):
                candidates.append(
                    {
                        "type": "return_bool",
                        "operator": str(node.value.value),
                        "line": node.lineno,
                    }
                )
    return candidates


def generate_mutation_report(file_path: str, test_file: str) -> dict:
    candidates = find_mutation_candidates(file_path)
    by_type: dict = {}
    for c in candidates:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
    report = {
        "file": file_path,
        "test_file": test_file,
        "candidates": len(candidates),
        "by_type": by_type,
    }
    logger.info(
        "Mutation candidates in %s: %d (%s)",
        os.path.basename(file_path),
        len(candidates),
        by_type,
    )
    return report


def calculate_mutation_score(total_mutations: int, killed_mutations: int) -> float:
    if total_mutations == 0:
        return 0.0
    score = round(killed_mutations / total_mutations * 100, 2)
    logger.info(
        "Mutation score: %.2f%% (%d/%d killed)", score, killed_mutations, total_mutations
    )
    return score


def run_mutation_analysis(directory: str) -> dict:
    bucket = os.environ.get("AWS_BUCKET_NAME", "")
    combined: dict = {
        "directory": directory,
        "files": [],
        "total_candidates": 0,
        "by_type": {},
    }
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git", ".mypy_cache"}]
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            try:
                report = generate_mutation_report(fpath, "")
                combined["files"].append(report)
                combined["total_candidates"] += report["candidates"]
                for k, v in report["by_type"].items():
                    combined["by_type"][k] = combined["by_type"].get(k, 0) + v
            except Exception as e:
                logger.error("Failed to analyze %s: %s", fpath, e)
    combined["generated_at"] = datetime.utcnow().isoformat()
    if bucket:
        date = datetime.utcnow().strftime("%Y/%m/%d")
        key = f"testing/mutation/{date}/report.json"
        s3 = boto3.client("s3")
        try:
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(combined, default=str),
                ContentType="application/json",
            )
            logger.info("Mutation report saved to s3://%s/%s", bucket, key)
        except Exception as e:
            logger.error("Failed to save mutation report: %s", e)
    logger.info(
        "Mutation analysis complete: %d files, %d candidates",
        len(combined["files"]),
        combined["total_candidates"],
    )
    return combined


if __name__ == "__main__":
    pass
