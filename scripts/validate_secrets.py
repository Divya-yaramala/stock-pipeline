import logging
import os
import sys
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_SECRETS: Dict[str, List[str]] = {
    "AWS": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_BUCKET_NAME"],
    "PostgreSQL": ["POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"],
    "Snowflake": ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"],
}

OPTIONAL_SECRETS: Dict[str, List[str]] = {
    "OpenAI": ["OPENAI_API_KEY"],
    "Slack": ["SLACK_WEBHOOK_URL"],
    "Email": ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"],
    "News API": ["NEWS_API_KEY"],
    "Kafka": ["KAFKA_BOOTSTRAP_SERVERS"],
}


def check_secrets() -> Dict[str, Any]:
    required_status: Dict[str, Any] = {}
    for service, vars_list in REQUIRED_SECRETS.items():
        missing = [v for v in vars_list if not os.environ.get(v, "")]
        required_status[str(service)] = {
            "status": "missing" if missing else "ok",
            "missing": missing,
        }

    optional_status: Dict[str, Any] = {}
    for service, vars_list in OPTIONAL_SECRETS.items():
        missing = [v for v in vars_list if not os.environ.get(v, "")]
        optional_status[str(service)] = {
            "status": "missing" if missing else "ok",
            "missing": missing,
        }

    all_required_present = all(v["status"] == "ok" for v in required_status.values())

    return {
        "required": required_status,
        "optional": optional_status,
        "all_required_present": all_required_present,
    }


def print_secrets_report(report: Dict[str, Any]) -> None:
    col = 14

    print("\n=== REQUIRED SECRETS ===")
    for service, data in report["required"].items():
        if data["status"] == "ok":
            status_str = "✅ ok"
        else:
            missing_list = ", ".join(data["missing"])
            status_str = f"❌ missing: {missing_list}"
        print(f"  {service:<{col}} {status_str}")

    print("\n=== OPTIONAL SECRETS ===")
    for service, data in report["optional"].items():
        if data["status"] == "ok":
            status_str = "✅ ok"
        else:
            missing_list = ", ".join(data["missing"])
            status_str = f"⚠️  missing: {missing_list}"
        print(f"  {service:<{col}} {status_str}")

    print()

    if not report["all_required_present"]:
        logger.error("Required secrets are missing — pipeline cannot run")
        sys.exit(1)


if __name__ == "__main__":
    result = check_secrets()
    print_secrets_report(result)
    sys.exit(0)
