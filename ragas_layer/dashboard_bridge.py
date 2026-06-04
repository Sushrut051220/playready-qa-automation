"""
dashboard_bridge.py
====================
Converts a completed RAGAs evaluation payload into DeepEval's
test_run_*.json format and writes it to the dashboard's eval_history/.

Called automatically at the end of run_ragas_evaluation() — no manual
steps needed. The dashboard picks it up within seconds via file watcher.

Usage (already wired in ragas_runner.py):
    from ragas_layer.dashboard_bridge import save_to_dashboard
    save_to_dashboard(payload)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

# ── Locate the dashboard folder ───────────────────────────────────────────────
# Works whether the dashboard is named 'dashboard', 'Deepeval_Foundry_dashboard'
# or 'Deepeval_Foundry_dashboard-main' inside the project root.

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def _find_eval_history() -> Path:
    """Find the dashboard's eval_history folder inside this project."""
    # Env var override — highest priority
    env_path = os.getenv("DEEPEVAL_RESULTS_FOLDER")
    if env_path:
        p = Path(env_path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Auto-detect: look for any folder containing run.py + eval_history/
    candidates = [
        PROJECT_ROOT / "dashboard",
        PROJECT_ROOT / "Deepeval_Foundry_dashboard",
        PROJECT_ROOT / "Deepeval_Foundry_dashboard-main",
    ]
    for candidate in candidates:
        if (candidate / "run.py").exists():
            hist = candidate / "eval_history"
            hist.mkdir(parents=True, exist_ok=True)
            return hist

    # Fallback — write next to the project root
    fallback = PROJECT_ROOT / "eval_history"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


# ── Metric name → display name mapping ───────────────────────────────────────
_METRIC_DISPLAY = {
    "answer_relevancy":            "AnswerRelevancy",
    "faithfulness":                "Faithfulness",
    "answer_accuracy":             "AnswerAccuracy",
    "context_precision":           "ContextPrecision",
    "context_utilization":         "ContextUtilization",
    "context_recall":              "ContextRecall",
    "context_relevance":           "ContextRelevance",
    "response_groundedness":       "ResponseGroundedness",
    "context_entity_recall":       "ContextEntityRecall",
    "noise_sensitivity_relevant":  "NoiseSensitivity(relevant)",
    "noise_sensitivity_irrelevant":"NoiseSensitivity(irrelevant)",
    "response_correctness":        "ResponseCorrectness",
    "answer_completeness":         "AnswerCompleteness",
}


# ── Converter ─────────────────────────────────────────────────────────────────

def _build_test_cases(payload: dict[str, Any]) -> list[dict]:
    rows        = payload.get("rows", [])
    thresholds  = payload.get("thresholds", {})
    provider    = payload.get("provider", {})
    eval_model  = provider.get("model", "unknown")
    test_cases  = []

    for row in rows:
        metrics_data = []
        row_passed   = True

        for metric_key, display_name in _METRIC_DISPLAY.items():
            score  = row.get(metric_key)
            result = row.get(f"{metric_key}_result", "SKIPPED")

            if result == "SKIPPED" or score is None:
                continue

            threshold = thresholds.get(metric_key, 0.5)
            success   = result == "PASS"
            if not success:
                row_passed = False

            metrics_data.append({
                "name":            display_name,
                "threshold":       threshold,
                "success":         success,
                "score":           round(float(score), 4),
                "reason":          f"RAGAs {display_name}: {score:.4f} "
                                   f"({'≥' if not metric_key.startswith('noise') else '≤'} "
                                   f"{threshold})",
                "evaluationModel": eval_model,
                "evaluationCost":  0.0,
            })

        latency = row.get("latency_seconds")

        test_cases.append({
            "name":             row.get("id") or row.get("question", "")[:60],
            "input":            row.get("question") or "",
            "actualOutput":     row.get("response") or "",
            "expectedOutput":   row.get("ground_truth") or None,
            "retrievalContext": row.get("retrieved_chunks") or [],
            "success":          row_passed,
            "metricsData":      metrics_data,
            "runDuration":      float(latency) if latency is not None else None,
            "evaluationCost":   0.0,
            "tags":             [],
        })

    return test_cases


def _build_metrics_scores(payload: dict[str, Any]) -> list[dict]:
    summary    = payload.get("summary", {})
    thresholds = payload.get("thresholds", {})
    rows       = payload.get("rows", [])
    scores     = []

    for metric_key, display_name in _METRIC_DISPLAY.items():
        avg = summary.get(metric_key)
        if avg is None:
            continue

        threshold = thresholds.get(metric_key, 0.5)
        is_noise  = metric_key.startswith("noise_sensitivity")

        row_scores, passes, fails = [], 0, 0
        for row in rows:
            score  = row.get(metric_key)
            result = row.get(f"{metric_key}_result", "SKIPPED")
            if score is None or result == "SKIPPED":
                continue
            row_scores.append(round(float(score), 4))
            if result == "PASS":
                passes += 1
            else:
                fails += 1

        scores.append({
            "metric": display_name,
            "scores": row_scores,
            "passes": passes,
            "fails":  fails,
            "errors": 0,
        })

    return scores


def save_to_dashboard(payload: dict[str, Any]) -> Path:
    """Convert RAGAs payload → DeepEval test_run_*.json and save to eval_history/."""
    test_cases     = _build_test_cases(payload)
    metrics_scores = _build_metrics_scores(payload)

    passed = sum(1 for tc in test_cases if tc["success"])
    failed = len(test_cases) - passed

    provider = payload.get("provider", {})

    run = {
        "testCases":              test_cases,
        "conversationalTestCases":[],
        "metricsScores":          metrics_scores,
        "testPassed":             passed,
        "testFailed":             failed,
        "runDuration":            None,
        "evaluationCost":         0.0,
        "hyperparameters": {
            "framework":    "ragas",
            "model":        provider.get("model", "unknown"),
            "provider":     provider.get("provider", "unknown"),
            "environment":  os.getenv("ENVIRONMENT", "development"),
            "version":      os.getenv("APP_VERSION", ""),
            "metrics_profile": payload.get("metrics_profile", ""),
            "dataset_size": payload.get("dataset_size", 0),
        },
        "identifier": "ragas-eval",
    }

    dest = _find_eval_history()
    fname = dest / f"test_run_{int(time.time())}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(run, f, indent=2, ensure_ascii=False)

    print(f"  Dashboard: {passed} passed / {failed} failed → {fname}")
    return fname
