import argparse
import logging
import os

from ingestion.workflow_automation_engine import AUTOMATED_WORKFLOWS, trigger_workflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_WORKFLOW_MAP = {str(w["workflow_id"]): w for w in AUTOMATED_WORKFLOWS}


def run_trigger_cli(args: argparse.Namespace) -> None:
    workflow_id = args.workflow_id
    reason = args.reason
    workflow = _WORKFLOW_MAP.get(workflow_id, {})

    if args.dry_run:
        print(f"\n[DRY RUN] Would trigger workflow: {workflow_id}")
        print(f"  Name: {workflow.get('name', 'unknown')}")
        print(f"  Schedule: {workflow.get('schedule', 'unknown')}")
        print(f"  Priority: {workflow.get('priority', 'unknown')}")
        print(f"  Steps: {workflow.get('steps', [])}")
        print(f"  Reason: {reason}")
        print("\nNo execution created (dry-run mode).")
        return

    bucket = os.getenv("AWS_BUCKET_NAME", "")
    execution_id = trigger_workflow(workflow_id, reason, bucket)
    print(f"\nWorkflow triggered: {workflow_id}")
    print(f"Execution ID: {execution_id}")
    print(f"Reason: {reason}")
    logger.info("Triggered %s: execution_id=%s", workflow_id, execution_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger a pipeline workflow")
    parser.add_argument(
        "--workflow-id",
        required=True,
        choices=["AW001", "AW002", "AW003", "AW004", "AW005"],
        help="Workflow to trigger",
    )
    parser.add_argument("--reason", default="manual", help="Trigger reason (default: manual)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without triggering",
    )
    parsed_args = parser.parse_args()
    run_trigger_cli(parsed_args)
