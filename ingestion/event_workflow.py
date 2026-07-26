import datetime
import json
import logging
from typing import Any, Dict, List

import boto3

from ingestion import slack_alerter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

WORKFLOW_TRIGGERS: List[Dict[str, Any]] = [
    {
        "trigger_id": "T001",
        "event": "anomaly_detected",
        "severity": "HIGH",
        "actions": ["send_slack_alert", "create_report", "log_audit"],
    },
    {
        "trigger_id": "T002",
        "event": "quality_gate_blocked",
        "severity": "CRITICAL",
        "actions": ["send_slack_alert", "trigger_remediation", "pause_pipeline"],
    },
    {
        "trigger_id": "T003",
        "event": "model_drift_detected",
        "severity": "MEDIUM",
        "actions": ["create_retraining_job", "send_slack_alert", "log_audit"],
    },
    {
        "trigger_id": "T004",
        "event": "sla_missed",
        "severity": "HIGH",
        "actions": ["send_slack_alert", "log_audit", "escalate"],
    },
    {
        "trigger_id": "T005",
        "event": "pipeline_completed",
        "severity": "LOW",
        "actions": ["update_dashboard", "send_daily_summary", "log_audit"],
    },
]


def find_matching_triggers(event_type: str) -> List[Dict[str, Any]]:
    matches = [t for t in WORKFLOW_TRIGGERS if str(t["event"]) == event_type]
    logger.info(f"Found {len(matches)} triggers for event: {event_type}")
    return matches


def execute_workflow_action(
    action: str,
    event_payload: Dict[str, Any],
    bucket: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    now = datetime.datetime.utcnow()
    timestamp = now.strftime("%Y%m%dT%H%M%S")
    date_path = now.strftime("%Y/%m/%d")
    success = False
    details = ""

    try:
        if action == "send_slack_alert":
            title = str(event_payload.get("event_type", "Pipeline Event"))
            message = json.dumps(event_payload)
            slack_alerter.send_slack_message(message=message, title=title, color="warning")
            success = True
            details = "Slack alert dispatched"

        elif action == "log_audit":
            key = f"workflows/audit/{date_path}/audit_{timestamp}.json"
            s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(event_payload))
            success = True
            details = f"Audit log saved: {key}"

        elif action == "create_report":
            key = f"workflows/reports/{date_path}/report_{timestamp}.json"
            s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(event_payload))
            success = True
            details = f"Report saved: {key}"

        elif action == "trigger_remediation":
            key = f"workflows/remediation/{date_path}/job_{timestamp}.json"
            s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(event_payload))
            success = True
            details = f"Remediation job saved: {key}"

        elif action == "pause_pipeline":
            key = f"workflows/flags/{date_path}/pause_{timestamp}.json"
            s3.put_object(
                Bucket=bucket, Key=key, Body=json.dumps({"paused": True, **event_payload})
            )
            success = True
            details = f"Pause flag saved: {key}"

        elif action == "update_dashboard":
            key = f"workflows/dashboard/{date_path}/update_{timestamp}.json"
            s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(event_payload))
            success = True
            details = f"Dashboard update saved: {key}"

        elif action == "send_daily_summary":
            key = f"workflows/summaries/{date_path}/summary_{timestamp}.json"
            s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(event_payload))
            success = True
            details = f"Summary request saved: {key}"

        elif action == "create_retraining_job":
            key = f"workflows/retraining/{date_path}/job_{timestamp}.json"
            s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(event_payload))
            success = True
            details = f"Retraining job saved: {key}"

        elif action == "escalate":
            key = f"workflows/escalations/{date_path}/escalation_{timestamp}.json"
            s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(event_payload))
            success = True
            details = f"Escalation record saved: {key}"

        else:
            details = f"Unknown action: {action}"

    except Exception as e:
        details = str(e)
        success = False

    logger.info(f"Action executed: {action} | success={success}")
    return {"action": action, "success": success, "details": details}


def process_event(
    event_type: str,
    event_payload: Dict[str, Any],
    bucket: str,
) -> Dict[str, Any]:
    enriched_payload = {"event_type": event_type, **event_payload}
    triggers = find_matching_triggers(event_type)
    triggers_fired = len(triggers)
    actions_executed = 0

    for trigger in triggers:
        for action in list(trigger.get("actions", [])):
            execute_workflow_action(str(action), enriched_payload, bucket)
            actions_executed += 1

    logger.info(
        f"Event processing complete: {event_type} "
        f"| triggers={triggers_fired} | actions={actions_executed}"
    )
    return {
        "event_type": event_type,
        "triggers_fired": triggers_fired,
        "actions_executed": actions_executed,
    }


def save_workflow_log(
    event_type: str,
    results: Dict[str, Any],
    bucket: str,
) -> bool:
    try:
        s3 = boto3.client("s3")
        now = datetime.datetime.utcnow()
        date_path = now.strftime("%Y/%m/%d")
        timestamp = now.strftime("%Y%m%dT%H%M%S")
        key = f"workflows/logs/{date_path}/{event_type}_{timestamp}.json"
        log_entry = {
            "event_type": event_type,
            "results": results,
            "logged_at": now.isoformat(),
        }
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(log_entry))
        logger.info(f"Workflow log saved: {key}")
        return True
    except Exception as e:
        logger.error(f"Failed to save workflow log: {e}")
        return False


def get_workflow_history(
    bucket: str,
    date: str,
) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3")
    prefix = f"workflows/logs/{date}/"
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    history: List[Dict[str, Any]] = []
    for obj in response.get("Contents", []):
        key = str(obj["Key"])
        resp = s3.get_object(Bucket=bucket, Key=key)
        entry = json.loads(resp["Body"].read())
        history.append(entry)
    logger.info(f"Found {len(history)} workflow logs for date: {date}")
    return history


def run_event_processing(
    events: List[Dict[str, Any]],
    bucket: str,
) -> Dict[str, Any]:
    total_events = len(events)
    total_triggers = 0
    total_actions = 0

    for event in events:
        event_type = str(event.get("event_type", ""))
        payload = {k: v for k, v in event.items() if k != "event_type"}
        result = process_event(event_type, payload, bucket)
        total_triggers += int(str(result.get("triggers_fired", 0)))
        total_actions += int(str(result.get("actions_executed", 0)))

    logger.info(
        f"Event processing summary: {total_events} events "
        f"| {total_triggers} triggers | {total_actions} actions"
    )
    return {
        "total_events": total_events,
        "triggers_fired": total_triggers,
        "actions_executed": total_actions,
    }


if __name__ == "__main__":
    pass
