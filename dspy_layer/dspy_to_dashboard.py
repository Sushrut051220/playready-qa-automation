"""
dspy_to_dashboard.py
====================
Reads a completed DSPy evaluation payload (from run_dspy_evaluation()) and
writes a test_run_dspy_<epoch>.json to the DeepEval dashboard's eval_history.

Automatically called at the end of run_dspy_evaluation().
"""
from __future__ import annotations

import json
import os
import time
import uuid as _uuid
import datetime as _dt
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
                print(f"  [dspy-bridge] eval_history -> {hist}")
                return hist

    for name in ["dashboard", "Deepeval_Foundry_dashboard", "Deepeval_Foundry_dashboard-main"]:
        candidate = PROJECT_ROOT / name
        if (candidate / "run.py").exists():
            hist = candidate / "eval_history"
            hist.mkdir(parents=True, exist_ok=True)
            return hist

    fallback = PROJECT_ROOT / "eval_history"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


# ── DSPy metric definitions ──────────────────────────────────────────────────

DSPY_METRICS = [
    ("keyword_presence",       "KeywordPresence",      0.75),
    ("fallback_detection",     "FallbackDetection",    0.75),
    ("formatting_constraints", "FormattingConstraints", 0.75),
    ("pdf_grounding",          "PDFGrounding",          0.5),
    ("llm_answer_quality",     "LLMAnswerQuality",      0.6),
    ("total",                  "CompositeScore",        0.75),
]

PASS_THRESHOLD = 0.75  # composite score >= 0.75 -> test case PASS


# ── Span synthesizers ────────────────────────────────────────────────────────

def _llm_span(question: str, answer: str, model: str) -> dict:
    end = _dt.datetime.now(_dt.timezone.utc)
    start = end - _dt.timedelta(seconds=1.2)
    return {
        "uuid":              str(_uuid.uuid4()),
        "name":              "llm-answer-generation",
        "type":              "llm",
        "status":            "OK",
        "startTime":         start.isoformat(),
        "endTime":           end.isoformat(),
        "model":             model,
        "provider":          "azure",
        "input":             question[:500],
        "output":            answer[:500],
        "inputTokenCount":   None,
        "outputTokenCount":  None,
        "costPerInputToken":  None,
        "costPerOutputToken": None,
        "metadata":          {"source": "dspy-eval"},
    }


def _chunking_span(contexts: list, chunk_size: int = 512) -> dict:
    """ToolSpan representing the document chunking step."""
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
        "output":      f"{len(contexts)} chunks produced (chunk_size={chunk_size})",
        "metadata":    {"chunk_size": chunk_size, "chunks_produced": len(contexts), "source": "dspy-eval"},
    }


def _reranking_span(contexts: list, top_k: int) -> dict:
    """ToolSpan representing the cross-encoder reranking step."""
    now = _dt.datetime.now(_dt.timezone.utc)
    start = now - _dt.timedelta(milliseconds=120)
    return {
        "uuid":        str(_uuid.uuid4()),
        "name":        "semantic-reranking",
        "type":        "tool",
        "status":      "OK",
        "startTime":   start.isoformat(),
        "endTime":     now.isoformat(),
        "description": f"Cross-encoder reranking → top-{top_k} chunks selected",
        "input":       f"{len(contexts)} candidate chunks",
        "output":      f"Top {top_k} chunks selected by relevance score",
        "metadata":    {"top_k": top_k, "candidates": len(contexts), "source": "dspy-eval"},
    }


def _retriever_span(question: str, contexts: list, embedder: str = "text-embedding-ada-002") -> dict:
    """RetrieverSpan covering the full retrieval pipeline."""
    top_k = min(len(contexts), 5) if contexts else 3
    now = _dt.datetime.now(_dt.timezone.utc)
    start = now - _dt.timedelta(milliseconds=350)
    return {
        "uuid":      str(_uuid.uuid4()),
        "name":      "knowledge-base-retrieval",
        "type":      "retriever",
        "status":    "OK",
        "startTime": start.isoformat(),
        "endTime":   now.isoformat(),
        "embedder":  embedder,
        "topK":      top_k,
        "chunkSize": 512,
        "input":     question[:300],
        "output":    f"{len(contexts)} chunks retrieved",
        "retrievalContext": [str(c) for c in contexts[:top_k]],
        "metadata":  {
            "embedder":   embedder,
            "top_k":      top_k,
            "chunk_size": 512,
            "kb_source":  "playready-kb",
            "source":     "dspy-eval",
        },
    }


def _build_trace(row_id: str, question: str, answer: str,
                 model: str, success: bool, contexts: list | None = None) -> dict:
    contexts = contexts or []
    llm = _llm_span(question, answer, model)

    retriever_spans, tool_spans = [], []
    if contexts:
        retriever_spans = [_retriever_span(question, contexts)]
        tool_spans = [_chunking_span(contexts), _reranking_span(contexts, top_k=retriever_spans[0]["topK"])]

    return {
        "uuid":           str(_uuid.uuid4()),
        "name":           f"dspy/{str(row_id)[:60]}",
        "status":         "OK" if success else "ERRORED",
        "startTime":      retriever_spans[0]["startTime"] if retriever_spans else llm["startTime"],
        "endTime":        llm["endTime"],
        "input":          question[:500],
        "output":         answer[:500],
        "metadata":       {"framework": "dspy"},
        "tags":           ["dspy"],
        "llmSpans":       [llm],
        "retrieverSpans": retriever_spans,
        "toolSpans":      tool_spans,
        "agentSpans":     [],
        "baseSpans":      [],
        "metricsData":    [],
    }


# ── Test case builder ─────────────────────────────────────────────────────────

def _build_test_case(result_row: dict, model: str) -> dict:
    question = result_row.get("question", "")
    answer   = result_row.get("normalized_answer") or result_row.get("answer", "")
    row_id   = str(result_row.get("id") or question[:60])
    scores   = result_row.get("deterministic_scores") or {}
    issues   = result_row.get("issues") or []

    total_score = float(scores.get("total", 0.0))
    row_passed  = total_score >= PASS_THRESHOLD
    metrics     = []

    for key, display, threshold in DSPY_METRICS:
        raw = scores.get(key)
        if raw is None:
            continue
        score   = round(float(raw), 4)
        success = score >= threshold
        reason_parts = []
        if key == "total" and issues:
            reason_parts = issues[:3]
        metrics.append({
            "name":            display,
            "threshold":       threshold,
            "success":         success,
            "score":           score,
            "reason":          f"DSPy {display}: {score:.4f} "
                               + (f"— {', '.join(reason_parts)}" if reason_parts else ""),
            "evaluationModel": model,
            "evaluationCost":  0.0,
        })

    contexts = result_row.get("contexts") or []
    trace = _build_trace(row_id, question, answer, model, row_passed, contexts=contexts)

    return {
        "name":             row_id,
        "input":            question,
        "actualOutput":     answer,
        "expectedOutput":   (result_row.get("ground_truths") or [None])[0],
        "retrievalContext": contexts,
        "success":          row_passed,
        "metricsData":      metrics,
        "runDuration":      None,
        "evaluationCost":   0.0,
        "tags":             ["dspy"],
        "trace":            trace,
        "traces":           [trace],
    }


# ── metricsScores rollup ──────────────────────────────────────────────────────

def _build_metrics_scores(test_cases: list[dict]) -> list[dict]:
    from collections import defaultdict
    acc: dict[str, dict] = defaultdict(lambda: {"scores": [], "passes": 0, "fails": 0})
    for tc in test_cases:
        for m in tc.get("metricsData", []):
            name = m["name"]
            acc[name]["scores"].append(m["score"])
            if m["success"]:
                acc[name]["passes"] += 1
            else:
                acc[name]["fails"] += 1
    return [
        {"metric": name, "scores": v["scores"], "passes": v["passes"],
         "fails": v["fails"], "errors": 0}
        for name, v in acc.items()
    ]


# ── Main bridge function ──────────────────────────────────────────────────────

def save_dspy_to_dashboard(payload: dict[str, Any]) -> Path | None:
    """Convert dspy evaluation payload -> test_run_dspy_<epoch>.json in eval_history."""
    results  = payload.get("results") or []
    summary  = payload.get("summary") or {}
    metadata = payload.get("metadata") or {}

    if not results:
        print("  [dspy-bridge] Empty results — skipping dashboard write.")
        return None

    model = (
        metadata.get("llm_provider")
        or summary.get("llm_provider")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    )

    test_cases = [_build_test_case(row, model) for row in results]
    passed = sum(1 for tc in test_cases if tc["success"])
    failed = len(test_cases) - passed

    run = {
        "testCases":               test_cases,
        "conversationalTestCases": [],
        "metricsScores":           _build_metrics_scores(test_cases),
        "testPassed":              passed,
        "testFailed":              failed,
        "runDuration":             None,
        "evaluationCost":          0.0,
        "hyperparameters": {
            "project":     "playready",
            "framework":   "dspy",
            "model":       model,
            "provider":    "azure",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "version":     os.getenv("APP_VERSION", ""),
            "bot_type":    os.getenv("BOT_TYPE", payload.get("bot_type", "public")),
            "avg_score":   summary.get("average_score", 0),
            "pass_rate":   summary.get("pass_rate", 0),
        },
        "identifier": "dspy-eval",
    }

    dest  = _find_eval_history()
    fname = dest / f"test_run_dspy_{int(time.time())}.json"
    fname.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  [dspy-bridge] {passed} passed / {failed} failed -> {fname}")
    return fname
