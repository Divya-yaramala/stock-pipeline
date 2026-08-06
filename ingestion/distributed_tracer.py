import datetime
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_active_spans: Dict[str, Dict[str, Any]] = {}
_active_traces: Dict[str, Dict[str, Any]] = {}


def start_trace(
    trace_name: str,
    ticker: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    raw = f"{trace_name}_{ticker}_{time.time()}"
    trace_id = hashlib.md5(raw.encode()).hexdigest()[:12]
    _active_traces[trace_id] = {
        "trace_name": trace_name,
        "ticker": ticker,
        "start_time": time.time(),
        "metadata": metadata or {},
        "spans": [],
    }
    logger.info("Trace started: %s (%s for %s)", trace_id, trace_name, ticker)
    return trace_id


def start_span(
    trace_id: str,
    span_name: str,
    parent_span_id: Optional[str] = None,
) -> str:
    raw = f"{trace_id}_{span_name}_{time.time()}"
    span_id = hashlib.md5(raw.encode()).hexdigest()[:12]
    _active_spans[span_id] = {
        "trace_id": trace_id,
        "span_name": span_name,
        "parent_span_id": parent_span_id,
        "start_time": time.time(),
    }
    logger.info("Span started: %s (%s) in trace %s", span_id, span_name, trace_id)
    return span_id


def end_span(
    trace_id: str,
    span_id: str,
    status: str,
    bucket: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    now = time.time()
    span_info = _active_spans.get(span_id, {})
    start_time = float(str(span_info.get("start_time", now)))
    span_name = str(span_info.get("span_name", "unknown"))
    duration_ms = (now - start_time) * 1000.0
    span_data: Dict[str, Any] = {
        "span_id": span_id,
        "trace_id": trace_id,
        "span_name": span_name,
        "status": status,
        "duration_ms": duration_ms,
        "metadata": metadata or {},
        "ended_at": datetime.datetime.utcnow().isoformat(),
    }
    if trace_id in _active_traces:
        _active_traces[trace_id]["spans"].append(span_data)
    _active_spans.pop(span_id, None)
    date_path = datetime.datetime.utcnow().strftime("%Y/%m/%d")
    key = f"traces/{date_path}/{trace_id}/{span_id}.json"
    try:
        client = boto3.client("s3")
        client.put_object(Bucket=bucket, Key=key, Body=json.dumps(span_data))
        logger.info("Span ended: %s (%.1f ms, status=%s)", span_name, duration_ms, status)
        return True
    except Exception as exc:
        logger.error("Failed to save span: %s", exc)
        return False


def end_trace(
    trace_id: str,
    status: str,
    bucket: str,
) -> bool:
    trace_data = _active_traces.get(trace_id, {})
    start_time = float(str(trace_data.get("start_time", time.time())))
    total_duration_ms = (time.time() - start_time) * 1000.0
    summary: Dict[str, Any] = {
        "trace_id": trace_id,
        "trace_name": str(trace_data.get("trace_name", "")),
        "ticker": str(trace_data.get("ticker", "")),
        "status": status,
        "total_duration_ms": total_duration_ms,
        "span_count": int(str(len(trace_data.get("spans", [])))),
        "ended_at": datetime.datetime.utcnow().isoformat(),
    }
    _active_traces.pop(trace_id, None)
    date_path = datetime.datetime.utcnow().strftime("%Y/%m/%d")
    key = f"traces/{date_path}/{trace_id}/summary.json"
    try:
        client = boto3.client("s3")
        client.put_object(Bucket=bucket, Key=key, Body=json.dumps(summary))
        logger.info("Trace ended: %s (%.1f ms, status=%s)", trace_id, total_duration_ms, status)
        return True
    except Exception as exc:
        logger.error("Failed to save trace summary: %s", exc)
        return False


def get_trace(trace_id: str, bucket: str) -> Dict[str, Any]:
    date_path = datetime.datetime.utcnow().strftime("%Y/%m/%d")
    prefix = f"traces/{date_path}/{trace_id}/"
    spans: List[Dict[str, Any]] = []
    try:
        client = boto3.client("s3")
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = str(obj["Key"])
                if "summary" not in key:
                    response = client.get_object(Bucket=bucket, Key=key)
                    spans.append(json.loads(response["Body"].read()))
    except Exception as exc:
        logger.error("Failed to retrieve trace: %s", exc)
    total_ms = sum(float(str(s.get("duration_ms", 0))) for s in spans)
    result: Dict[str, Any] = {
        "trace_id": trace_id,
        "spans": spans,
        "total_duration_ms": total_ms,
    }
    logger.info("Trace retrieved: %s (%d spans)", trace_id, len(spans))
    return result


def analyze_trace(trace: Dict[str, Any]) -> Dict[str, Any]:
    spans: List[Dict[str, Any]] = list(trace.get("spans", []))
    error_count = sum(1 for s in spans if str(s.get("status", "")) == "error")
    slowest_span = ""
    max_duration = -1.0
    for span in spans:
        dur = float(str(span.get("duration_ms", 0)))
        if dur > max_duration:
            max_duration = dur
            slowest_span = str(span.get("span_name", ""))
    total_ms = float(str(trace.get("total_duration_ms", 0)))
    result: Dict[str, Any] = {
        "slowest_span": slowest_span,
        "error_count": error_count,
        "total_ms": total_ms,
    }
    logger.info("Trace analyzed: slowest=%s, errors=%d", slowest_span, error_count)
    return result


def run_pipeline_with_tracing(ticker: str, bucket: str) -> str:
    trace_id = start_trace("pipeline_run", ticker)
    steps = ["fetch_data", "validate", "detect_anomaly", "predict", "generate_insights"]
    for step in steps:
        span_id = start_span(trace_id, step)
        end_span(trace_id, span_id, "ok", bucket)
    end_trace(trace_id, "ok", bucket)
    logger.info("Pipeline Trace Complete for %s: %s", ticker, trace_id)
    return trace_id


if __name__ == "__main__":
    pass
