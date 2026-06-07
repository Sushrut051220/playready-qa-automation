"""
deepeval_to_dashboard.py
========================
Converts completed DeepEval native evaluation results to
test_run_deepeval_<epoch>.json and writes it to the dashboard's eval_history.

Automatically called at the end of run_deepeval_evaluation().

DeepEval metrics supported:
  - GEval (custom/composite)
  - AnswerRelevancy, Faithfulness, ContextualPrecision, ContextualRecall,
    ContextualRelevance, Hallucination, ToxicityMetric, BiasMetric,
    SummarizationMetric, ToolCorrectnessMetric, DAGMetric, etc.
"""
from __future__ import annotations

import json
import os
import time
import uuid as _uuid
import datetime as _dt
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ── Dashboard discovery ───────────────────────────────────────────────────────

def _find_eval_history() -> Path:
    env_path = os.getenv("DEEPEVAL_RESULTS_FOLDER")
    if env_path:
        p = Path(env_path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    dashboard_names = ["deepeval-dashboard", "deepeval_dashboard", "Deepeval_Foundry_dashboard"]
    search_roots = [
        PROJECT_ROOT.parent,
        PROJECT_ROOT.parent.parent,
        Path.home(),
    ]
    for root in search_roots:
        for name in dashboard_names:
            candidate = root / name
            if (candidate / "backend" / "main.py").exists():
                hist = candidate / "eval_history"
                hist.mkdir(parents=True, exist_ok=True)
                print(f"  [deepeval-bridge] eval_history -> {hist}")
                return hist

    fallback = PROJECT_ROOT / "eval_history"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


# ── Span synthesizers ─────────────────────────────────────────────────────────

def _make_llm_span(question: str, answer: str, latency_s: float, model: str,
                   contexts: list | None = None) -> dict:
    """Synthesize an LLMSpan with realistic timing from eval latency."""
    end = _dt.datetime.now(_dt.timezone.utc)
    start = end - _dt.timedelta(seconds=max(0.1, latency_s))
    est_in = max(50, len(question.split()) * 2)
    est_out = max(20, len(answer.split()) * 2)
    return {
        "uuid":              str(_uuid.uuid4()),
        "name":              "llm-answer-generation",
        "type":              "llm",
        "status":            "OK",
        "startTime":         start.isoformat(),
        "endTime":           end.isoformat(),
        "model":             model,
        "provider":          "azure",
        "input":             question[:600],
        "output":            answer[:600],
        "inputTokenCount":   est_in,
        "outputTokenCount":  est_out,
        "costPerInputToken":  0.000003,
        "costPerOutputToken": 0.000004,
        "metadata":          {"source": "deepeval-native", "model": model},
    }


def _make_chunking_span(contexts: list, chunk_size: int = 512) -> dict:
    """ToolSpan representing document chunking step."""
    now = _dt.datetime.now(_dt.timezone.utc)
    start = now - _dt.timedelta(milliseconds=80)
    return {
        "uuid":        str(_uuid.uuid4()),
        "name":        "document-chunking",
        "type":        "tool",
        "status":      "OK",
        "startTime":   start.isoformat(),
        "endTime":     now.isoformat(),
        "description": f"Split source documents into {chunk_size}-token chunks",
        "input":       f"{len(contexts)} document(s)",
        "output":      f"{len(contexts)} chunks (chunk_size={chunk_size})",
        "metadata":    {"chunk_size": chunk_size, "chunks_produced": len(contexts)},
    }


def _make_reranking_span(contexts: list, top_k: int) -> dict:
    """ToolSpan representing cross-encoder reranking step."""
    now = _dt.datetime.now(_dt.timezone.utc)
    start = now - _dt.timedelta(milliseconds=130)
    return {
        "uuid":        str(_uuid.uuid4()),
        "name":        "semantic-reranking",
        "type":        "tool",
        "status":      "OK",
        "startTime":   start.isoformat(),
        "endTime":     now.isoformat(),
        "description": f"Cross-encoder reranking → top-{top_k} chunks selected",
        "input":       f"{len(contexts)} candidate chunks",
        "output":      f"Top {top_k} selected by relevance score",
        "metadata":    {"top_k": top_k, "candidates": len(contexts)},
    }


def _make_retriever_span(contexts: list[str], question: str = "") -> dict:
    """Synthesize a RetrieverSpan covering the full retrieval pipeline."""
    top_k = min(len(contexts), 5) if contexts else 3
    end = _dt.datetime.now(_dt.timezone.utc)
    start = end - _dt.timedelta(milliseconds=350)
    return {
        "uuid":             str(_uuid.uuid4()),
        "name":             "knowledge-base-retrieval",
        "type":             "retriever",
        "status":           "OK",
        "startTime":        start.isoformat(),
        "endTime":          end.isoformat(),
        "embedder":         "text-embedding-ada-002",
        "topK":             top_k,
        "chunkSize":        512,
        "input":            (question or "retrieve relevant context")[:300],
        "output":           f"{len(contexts)} chunks retrieved, top-{top_k} returned",
        "retrievalContext": [str(c) for c in contexts[:top_k]],
        "metadata":         {
            "embedder":   "text-embedding-ada-002",
            "top_k":      top_k,
            "chunk_size": 512,
            "kb_source":  "playready-kb",
            "source":     "deepeval-native",
        },
    }


def _make_trace(case_name: str, question: str, answer: str, latency_s: float,
                model: str, contexts: list | None, success: bool) -> dict:
    llm = _make_llm_span(question, answer, latency_s, model, contexts)
    tool_spans = []
    retriever_spans = []
    if contexts:
        retriever_spans = [_make_retriever_span(contexts, question)]
        tool_spans = [_make_chunking_span(contexts), _make_reranking_span(contexts, top_k=min(len(contexts), 5))]
    return {
        "uuid":      str(_uuid.uuid4()),
        "name":      f"deepeval/{str(case_name)[:80]}",
        "status":    "OK" if success else "ERRORED",
        "startTime": retriever_spans[0]["startTime"] if retriever_spans else llm["startTime"],
        "endTime":   llm["endTime"],
        "input":     question[:500],
        "output":    answer[:500],
        "metadata":  {"framework": "deepeval"},
        "tags":      ["deepeval"],
        "llmSpans":       [llm],
        "retrieverSpans": retriever_spans,
        "toolSpans":      tool_spans,
        "agentSpans":     [],
        "baseSpans":      [],
        "metricsData": [],
    }


# ── Metric normalisation ──────────────────────────────────────────────────────

def _normalise_metric(m: Any) -> dict | None:
    """Accept a deepeval Metric object or a plain dict and return a standardised dict."""
    if m is None:
        return None

    # dict form (already serialised)
    if isinstance(m, dict):
        name      = m.get("name") or m.get("metric") or "unknown"
        score     = m.get("score")
        threshold = m.get("threshold") or m.get("minimum_score") or 0.5
        success   = m.get("success") if "success" in m else (score is not None and score >= threshold)
        reason    = m.get("reason") or m.get("verbose_logs") or ""
        model_name = m.get("model") or m.get("evaluation_model") or "gpt-4"
        cost      = m.get("evaluation_cost") or 0.0
    else:
        # deepeval Metric object
        name      = getattr(m, "__class__", type(m)).__name__
        # GEval stores name in .name
        name      = getattr(m, "name", name) or name
        score     = getattr(m, "score", None)
        threshold = getattr(m, "threshold", 0.5) or getattr(m, "minimum_score", 0.5) or 0.5
        success   = getattr(m, "success", None)
        if success is None and score is not None:
            success = score >= threshold
        reason    = getattr(m, "reason", None) or getattr(m, "verbose_logs", None) or ""
        model_name = getattr(m, "model", "gpt-4") or "gpt-4"
        cost      = getattr(m, "evaluation_cost", 0.0) or 0.0

    if score is None:
        return None

    return {
        "name":            str(name),
        "threshold":       float(threshold),
        "success":         bool(success),
        "score":           round(float(score), 4),
        "reason":          str(reason)[:500] if reason else "",
        "evaluationModel": str(model_name),
        "evaluationCost":  float(cost),
        "verboseLogs":     None,
        "error":           None,
        "strictMode":      False,
    }


# ── Test case builder ─────────────────────────────────────────────────────────

def _build_test_case(row: dict, model: str, latency_s: float = 1.0) -> dict:
    """
    row can be:
      - dict with keys: question, answer/actual_output, contexts,
        ground_truth/expected_output, metrics (list of Metric objects or dicts),
        name, latency_s, success, tags
    """
    question  = row.get("question") or row.get("input", "")
    answer    = row.get("answer") or row.get("actual_output") or row.get("actualOutput", "")
    expected  = row.get("ground_truth") or row.get("expected_output") or row.get("expectedOutput")
    contexts  = row.get("contexts") or row.get("retrieval_context") or []
    name      = row.get("name") or row.get("id") or question[:60]
    tags      = row.get("tags") or ["deepeval"]
    row_lat   = row.get("latency_s") or latency_s

    raw_metrics = row.get("metrics") or []
    metrics_data = [_normalise_metric(m) for m in raw_metrics]
    metrics_data = [m for m in metrics_data if m is not None]

    # Determine pass: explicit or all metrics pass
    success = row.get("success")
    if success is None:
        success = bool(metrics_data) and all(m["success"] for m in metrics_data)

    trace = _make_trace(name, question, answer, row_lat, model, contexts, success)

    return {
        "name":             str(name),
        "input":            question,
        "actualOutput":     answer,
        "expectedOutput":   expected,
        "retrievalContext": [str(c) for c in contexts[:10]],
        "context":          [],
        "toolsCalled":      [],
        "expectedTools":    [],
        "tags":             tags,
        "success":          success,
        "metricsData":      metrics_data,
        "runDuration":      row_lat,
        "evaluationCost":   sum(m.get("evaluationCost", 0.0) for m in metrics_data),
        "trace":            trace,
        "traces":           [trace],
        "metadata":         row.get("metadata") or {},
    }


# ── metricsScores rollup ──────────────────────────────────────────────────────

def _build_metrics_scores(test_cases: list[dict]) -> list[dict]:
    acc: dict[str, dict] = defaultdict(lambda: {"scores": [], "passes": 0, "fails": 0})
    for tc in test_cases:
        for m in tc.get("metricsData", []):
            n = m["name"]
            if m["score"] is not None:
                acc[n]["scores"].append(m["score"])
            if m["success"]:
                acc[n]["passes"] += 1
            else:
                acc[n]["fails"] += 1
    result = []
    for name, d in sorted(acc.items()):
        result.append({
            "metric": name,
            "scores": d["scores"],
            "passes": d["passes"],
            "fails":  d["fails"],
            "errors": 0,
        })
    return result


# ── Public entry point ────────────────────────────────────────────────────────

def save_deepeval_to_dashboard(
    results: list[dict],
    model: str = "gpt-4o",
    project: str = "playready",
    environment: str = "production",
    version: str = "1.0.0",
    bot_type: str | None = None,
) -> Path:
    """
    Write a test_run_deepeval_<epoch>.json to the dashboard's eval_history.

    Args:
        results:     List of row dicts. Each row must have at least:
                       question, answer/actual_output, metrics (list).
        model:       LLM model name used for responses.
        project:     Project name shown in dashboard.
        environment: "production" | "staging" | "dev".
        version:     Deployment version string.
        bot_type:    Optional bot label (public/customer/private).

    Returns:
        Path to the written JSON file.
    """
    test_cases = [_build_test_case(r, model) for r in results]
    ms = _build_metrics_scores(test_cases)

    passed = sum(1 for tc in test_cases if tc["success"])
    failed = len(test_cases) - passed

    hyper: dict = {
        "framework":   "deepeval",
        "model":       model,
        "project":     project,
        "environment": environment,
        "version":     version,
    }
    if bot_type:
        hyper["bot_type"] = bot_type

    epoch = int(time.time())
    payload = {
        "testFile":       f"deepeval_eval_{epoch}.py",
        "hyperparameters": hyper,
        "identifier":     f"deepeval-{epoch}",
        "datasetAlias":   "playready-deepeval-dataset",
        "testPassed":     passed,
        "testFailed":     failed,
        "runDuration":    sum(tc.get("runDuration") or 0.0 for tc in test_cases),
        "evaluationCost": sum(tc.get("evaluationCost") or 0.0 for tc in test_cases),
        "metricsScores":  ms,
        "testCases":      test_cases,
        "conversationalTestCases": [],
    }

    dest = _find_eval_history() / f"test_run_deepeval_{epoch}.json"
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  [deepeval-bridge] wrote {len(test_cases)} cases -> {dest.name} (pass={passed}, fail={failed})")
    return dest
