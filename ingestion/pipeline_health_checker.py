import logging
import os
import subprocess
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_KEY_MODULES = [
    "ingestion.fetch_stocks",
    "ingestion.anomaly_detector",
    "ingestion.price_predictor",
    "ingestion.data_validator",
    "ingestion.config_manager",
    "ingestion.lakehouse_manager",
    "ingestion.delta_versioner",
    "ingestion.distributed_tracer",
    "ingestion.observability_dashboard",
    "ingestion.adaptive_model",
    "ingestion.online_feature_engineer",
    "ingestion.pipeline_validator",
    "ingestion.contract_enforcer",
    "ingestion.workflow_automation_engine",
    "ingestion.pipeline_recovery_manager",
]

_REQUIRED_ENV_VARS = [
    "AWS_BUCKET_NAME",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_REGION",
    "SNOWFLAKE_ACCOUNT",
    "POSTGRES_HOST",
    "OPENAI_API_KEY",
]


def check_all_modules_importable() -> Dict[str, Any]:
    failed: List[str] = []
    importable = 0
    for module in _KEY_MODULES:
        try:
            __import__(module)
            importable += 1
        except Exception as exc:
            failed.append(f"{module}: {exc}")
    result: Dict[str, Any] = {
        "total": len(_KEY_MODULES),
        "importable": importable,
        "failed": failed,
    }
    logger.info("Module import check: %d/%d importable", importable, len(_KEY_MODULES))
    return result


def check_test_suite_health() -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            ["python", "-m", "pytest", "tests/", "--co", "-q", "--tb=no"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = proc.stdout + proc.stderr
        lines = [line for line in output.splitlines() if line.strip()]
        test_count = sum(1 for line in lines if "::" in line)
        test_files = len(set(line.split("::")[0] for line in lines if "::" in line))
        status = "ok" if proc.returncode == 0 else "error"
    except Exception as exc:
        logger.error("Test suite check failed: %s", exc)
        test_count = 0
        test_files = 0
        status = "error"
    result: Dict[str, Any] = {
        "test_files": test_files,
        "test_count": test_count,
        "status": status,
    }
    logger.info(
        "Test suite health: %d tests in %d files, status=%s", test_count, test_files, status
    )
    return result


def check_dependencies_installed() -> Dict[str, Any]:
    missing: List[str] = []
    installed = 0
    requirements_path = os.path.join(os.path.dirname(__file__), "..", "requirements.txt")
    packages: List[str] = []
    try:
        with open(requirements_path) as f:
            packages = [
                line.strip().split("==")[0].split(">=")[0].split("<=")[0]
                for line in f
                if line.strip() and not line.startswith("#")
            ]
    except Exception as exc:
        logger.error("Could not read requirements.txt: %s", exc)
        return {"total": 0, "installed": 0, "missing": [str(exc)]}
    for pkg in packages:
        try:
            __import__(pkg.replace("-", "_").replace(".", "_").lower())
            installed += 1
        except ImportError:
            try:
                import importlib

                importlib.import_module(pkg.replace("-", "_"))
                installed += 1
            except ImportError:
                missing.append(pkg)
    result: Dict[str, Any] = {
        "total": len(packages),
        "installed": installed,
        "missing": missing,
    }
    logger.info("Dependency check: %d/%d installed", installed, len(packages))
    return result


def check_environment_variables() -> Dict[str, Any]:
    missing: List[str] = []
    present = 0
    for var in _REQUIRED_ENV_VARS:
        if os.environ.get(var):
            present += 1
        else:
            missing.append(var)
    result: Dict[str, Any] = {
        "required_present": present,
        "required_total": len(_REQUIRED_ENV_VARS),
        "missing": missing,
    }
    logger.info("Env var check: %d/%d required vars present", present, len(_REQUIRED_ENV_VARS))
    return result


def run_full_health_check() -> Dict[str, Any]:
    checks: Dict[str, Any] = {}

    checks["modules"] = check_all_modules_importable()
    checks["tests"] = check_test_suite_health()
    checks["dependencies"] = check_dependencies_installed()
    checks["env_vars"] = check_environment_variables()

    module_score = (
        float(str(checks["modules"]["importable"])) / float(str(checks["modules"]["total"])) * 100
        if checks["modules"]["total"] > 0
        else 0.0
    )
    test_score = 100.0 if checks["tests"]["status"] == "ok" else 50.0
    dep_total = float(str(checks["dependencies"]["total"]))
    dep_installed = float(str(checks["dependencies"]["installed"]))
    dep_score = (dep_installed / dep_total * 100) if dep_total > 0 else 100.0
    env_total = float(str(checks["env_vars"]["required_total"]))
    env_present = float(str(checks["env_vars"]["required_present"]))
    env_score = (env_present / env_total * 100) if env_total > 0 else 0.0

    overall_score = (module_score + test_score + dep_score + env_score) / 4.0

    if overall_score >= 90:
        grade = "A"
    elif overall_score >= 80:
        grade = "B"
    elif overall_score >= 70:
        grade = "C"
    elif overall_score >= 60:
        grade = "D"
    else:
        grade = "F"

    result: Dict[str, Any] = {
        "overall_score": overall_score,
        "grade": grade,
        "checks": checks,
    }
    logger.info("Full Health Check Complete: %.1f/100 Grade: %s", overall_score, grade)
    return result


if __name__ == "__main__":
    result = run_full_health_check()
    print(f"Health Score: {result['overall_score']}/100 (Grade: {result['grade']})")
