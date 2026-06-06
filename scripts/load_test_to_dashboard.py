from __future__ import annotations

"""
load_test_to_dashboard.py
=========================
Converts agent_load_details_*.json (produced by run_agent_load_test.py)
into DeepEval's test_run_*.json format so the dashboard Latency page,
Projects view, SLOs, and bug detector all pick up load test results.

Zero changes to run_agent_load_test.py output — reads it as-is.
Writes to the same eval_history/ folder the RAGAS bridge uses, under
a separate project so load test runs never mix with eval runs.

Usage:
    python scripts/load_test_to_dashboard.py
        [--details   path/to/agent_load_details_*.json]   # auto-finds latest if omitted
        [--summary   path/to/agent_load_summary_*.json]   # auto-finds latest if omitted
        [--bot-type  public|customer|private]             # default: public
        [--output-dir path/to/eval_history]               # default: auto-detect
"""

import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# SLA latency threshold from run_agent_load_test.py (seconds)
LATENCY_SLA_AVG = 10.0
LATENCY_SLA_P95 = 12.0

# ── Locate eval_history (same logic as dashboard_bridge.py) ──────────────────

def _find_eval_history(override: str | None = None) -> Path:
    if override:
        p = Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p

    env_path = os.getenv("DEEPEVAL_RESULTS_FOLDER")
    if env_path:
        p = Path(env_path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    candidates = [
        PROJECT_ROOT / "dashboard",
        PROJECT_ROOT / "Deepeval_Foundry_dashboard",
        PROJECT_ROOT / "Deepeval_Foundry_dashboard-main",
    ]
    for c in candidates:
        if (c / "run.py").exists():
            hist = c / "eval_history"
            hist.mkdir(parents=True, exist_ok=True)
            return hist

    fallback = PROJECT_ROOT / "eval_history"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


# ── Auto-find latest load test output files ───────────────────────────────────

def _latest_file(pattern: str, search_dirs: list[Path]) -> Path | None:
    matches = []
    for d in search_dirs:
        if d.exists():
            matches.extend(d.glob(pattern))
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


# ── Reconstruct ISO timestamps when not present in older output files ─────────

def _reconstruct_iso(latency_seconds: float, approx_end: datetime) -> tuple[str, str]:
    """Fall back when request_start_iso / request_end_iso are absent."""
    end = approx_end
    start = end - timedelta(seconds=latency_seconds)
    fmt = "%Y-%m-%dT%H:%M:%S.%f"
    return start.strftime(fmt)[:-3] + "Z", end.strftime(fmt)[:-3] + "Z"


# ── Build one test case (one llmSpan per agent request) ──────────────────────

def _build_test_case(record: dict, agent_name: str, agent_version: str,
                     approx_end: datetime) -> dict:
    request_id  = record.get("request_id", str(uuid.uuid4()))
    question    = record.get("question", "")
    answer      = record.get("answer", "")
    status      = record.get("run_status", "failed")
    latency     = float(record.get("latency_seconds", 0.0))
    token_usage = record.get("token_usage") or {}
    error_msg   = record.get("error_message", "")

    start_iso = record.get("request_start_iso")
    end_iso   = record.get("request_end_iso")
    if not start_iso or not end_iso:
        start_iso, end_iso = _reconstruct_iso(latency, approx_end)

    success      = status == "completed"
    span_status  = "SUCCESS" if success else "ERRORED"
    latency_pass = latency <= LATENCY_SLA_AVG

    metrics_data = [
        {
            "name":            "Latency",
            "score":           round(latency, 4),
            "success":         latency_pass,
            "threshold":       LATENCY_SLA_AVG,
            "reason":          f"Agent response time {latency:.2f}s "
                               f"({'≤' if latency_pass else '>'} {LATENCY_SLA_AVG}s SLA)",
            "evaluationModel": "sla-check",
            "evaluationCost":  0.0,
        },
        {
            "name":            "TokenUsage",
            "score":           float(token_usage.get("total_tokens", 0)),
            "success":         token_usage.get("total_tokens", 0) <= 8000,
            "threshold":       8000.0,
            "reason":          f"Total tokens: {token_usage.get('total_tokens', 0)}",
            "evaluationModel": "sla-check",
            "evaluationCost":  0.0,
        },
    ]

    if not success:
        metrics_data.append({
            "name":            "RequestSuccess",
            "score":           0.0,
            "success":         False,
            "threshold":       1.0,
            "reason":          f"Request failed: {error_msg[:200]}",
            "evaluationModel": "sla-check",
            "evaluationCost":  0.0,
        })

    span_uuid = str(uuid.uuid4())
    trace_uuid = str(uuid.uuid4())

    llm_span = {
        "uuid":               span_uuid,
        "name":               f"{agent_name}:{agent_version}",
        "type":               "llm",
        "status":             span_status,
        "startTime":          start_iso,
        "endTime":            end_iso,
        "model":              agent_name,
        "provider":           "azure-foundry",
        "input":              question,
        "output":             answer,
        "inputTokenCount":    token_usage.get("prompt_tokens", 0),
        "outputTokenCount":   token_usage.get("completion_tokens", 0),
        "costPerInputToken":  0.0,
        "costPerOutputToken": 0.0,
        "metadata":           {"request_id": request_id, "error": error_msg or None},
    }

    trace = {
        "uuid":            trace_uuid,
        "name":            request_id,
        "status":          span_status,
        "startTime":       start_iso,
        "endTime":         end_iso,
        "input":           question,
        "output":          answer,
        "metadata":        {"request_id": request_id},
        "tags":            ["load-test"],
        "llmSpans":        [llm_span],
        "retrieverSpans":  [],
        "toolSpans":       [],
        "agentSpans":      [],
        "baseSpans":       [],
        "metricsData":     [],
    }

    return {
        "name":             request_id,
        "input":            question,
        "actualOutput":     answer,
        "expectedOutput":   None,
        "success":          success and latency_pass,
        "runDuration":      latency,
        "evaluationCost":   0.0,
        "tags":             ["load-test", f"status-{status}"],
        "metricsData":      metrics_data,
        "trace":            trace,
    }


# ── Build aggregated metricsScores block ──────────────────────────────────────

def _build_metrics_scores(test_cases: list[dict]) -> list[dict]:
    latency_scores, latency_passes, latency_fails = [], 0, 0
    token_scores, token_passes, token_fails = [], 0, 0

    for tc in test_cases:
        for m in tc.get("metricsData", []):
            if m["name"] == "Latency":
                latency_scores.append(m["score"])
                if m["success"]:
                    latency_passes += 1
                else:
                    latency_fails += 1
            elif m["name"] == "TokenUsage":
                token_scores.append(m["score"])
                if m["success"]:
                    token_passes += 1
                else:
                    token_fails += 1

    return [
        {
            "metric":  "Latency",
            "scores":  latency_scores,
            "passes":  latency_passes,
            "fails":   latency_fails,
            "errors":  0,
        },
        {
            "metric":  "TokenUsage",
            "scores":  token_scores,
            "passes":  token_passes,
            "fails":   token_fails,
            "errors":  0,
        },
    ]


# ── Main converter ────────────────────────────────────────────────────────────

def convert(details_path: Path, summary_path: Path | None,
            bot_type: str, output_dir: str | None) -> Path:

    records = json.loads(details_path.read_text(encoding="utf-8-sig"))
    print(f"  Loaded {len(records)} request records from {details_path.name}")

    summary_pkg = {}
    if summary_path and summary_path.exists():
        summary_pkg = json.loads(summary_path.read_text(encoding="utf-8-sig"))
        print(f"  Loaded summary from {summary_path.name}")

    summary     = summary_pkg.get("summary", {})
    agent_name  = summary.get("agent_name", os.getenv("FOUNDRY_AGENT_NAME", "Agent"))
    agent_ver   = str(summary.get("agent_version", os.getenv("FOUNDRY_AGENT_VERSION", "")))
    total_dur   = summary.get("total_duration_seconds")
    users       = summary.get("users", "")
    repeat      = summary.get("repeat", "")

    # Approximate run end time from file mtime if no explicit timestamps
    approx_end = datetime.fromtimestamp(details_path.stat().st_mtime, tz=timezone.utc)

    test_cases = [
        _build_test_case(r, agent_name, agent_ver, approx_end)
        for r in records
    ]

    passed = sum(1 for tc in test_cases if tc["success"])
    failed = len(test_cases) - passed

    run = {
        "testCases":               test_cases,
        "conversationalTestCases": [],
        "metricsScores":           _build_metrics_scores(test_cases),
        "testPassed":              passed,
        "testFailed":              failed,
        "runDuration":             total_dur,
        "evaluationCost":          0.0,
        "hyperparameters": {
            "project":       f"playready-loadtest-{bot_type}",
            "bot_type":      bot_type,
            "environment":   os.getenv("ENVIRONMENT", "development"),
            "agent_name":    agent_name,
            "agent_version": agent_ver,
            "users":         users,
            "repeat":        repeat,
            "sla_p95_target_seconds": LATENCY_SLA_P95,
            "source_file":   details_path.name,
        },
        "identifier": f"load-test-{bot_type}",
    }

    dest  = _find_eval_history(output_dir)
    fname = dest / f"test_run_loadtest_{int(time.time())}.json"
    fname.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n  Dashboard file written: {fname}")
    print(f"  Project : playready-loadtest-{bot_type}")
    print(f"  Passed  : {passed} / {len(test_cases)}")
    print(f"  Failed  : {failed} / {len(test_cases)}")
    return fname


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convert load test output → DeepEval dashboard format"
    )
    parser.add_argument("--details",    help="Path to agent_load_details_*.json (auto-finds latest if omitted)")
    parser.add_argument("--summary",    help="Path to agent_load_summary_*.json (auto-finds latest if omitted)")
    parser.add_argument("--bot-type",   default="public", choices=["public", "customer", "private"])
    parser.add_argument("--output-dir", help="Path to eval_history/ folder (auto-detects if omitted)")
    args = parser.parse_args()

    search_dirs = [
        PROJECT_ROOT / "reports" / "bridge",
        PROJECT_ROOT / "reports",
        PROJECT_ROOT,
    ]

    details_path = Path(args.details) if args.details else _latest_file("agent_load_details_*.json", search_dirs)
    summary_path = Path(args.summary) if args.summary else _latest_file("agent_load_summary_*.json", search_dirs)

    if not details_path or not details_path.exists():
        print("ERROR: No agent_load_details_*.json found. Run run_agent_load_test.py first "
              "or pass --details <path>")
        raise SystemExit(1)

    print(f"Converting: {details_path}")
    convert(details_path, summary_path, args.bot_type, args.output_dir)


if __name__ == "__main__":
    main()
