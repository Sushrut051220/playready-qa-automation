from __future__ import annotations
# __FULL_DEEP_TRACER_INJECTED__
# Auto-injected: deep-tracing for the dashboard's Trace Viewer.
# Defensive: if the local exporter is missing, _T is a no-op so the
# pipeline keeps working without any behavior change.
try:
    from local_trace_exporter import get_tracer as _get_tracer  # type: ignore
    _T = _get_tracer()
    _TRACING_OK = True
except Exception:
    class _NoopTracer:
        from contextlib import contextmanager
        _pending_by_case = {}
        def set_case_key(self, *a, **kw): pass
        @contextmanager
        def span(self, *a, **kw):
            class S:
                output = None
                metadata = {}
            yield S()
        def observe(self, *a, **kw):
            def deco(f):
                return f
            return deco
    _T = _NoopTracer()
    _TRACING_OK = False

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

import json
import os
import time
import uuid as _uuid
import datetime as _dt
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def _find_eval_history() -> Path:
    """Find the dashboard's eval_history folder.

    Search order:
    1. DEEPEVAL_RESULTS_FOLDER env var (highest priority)
    2. Known sibling/parent paths (deepeval-dashboard next to or above this project)
    3. Dashboard folder inside the project root
    4. Project-root fallback (last resort)
    """
    env_path = os.getenv("DEEPEVAL_RESULTS_FOLDER")
    if env_path:
        p = Path(env_path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Search for deepeval-dashboard in parent directories (handles OneDrive nesting)
    dashboard_names = ["deepeval-dashboard", "deepeval_dashboard", "Deepeval_Foundry_dashboard"]
    search_roots = [
        PROJECT_ROOT.parent,              # sibling of project
        PROJECT_ROOT.parent.parent,       # e.g. OneDrive root
        Path.home(),                      # C:\Users\<user>
    ]
    for root in search_roots:
        for name in dashboard_names:
            candidate = root / name
            if (candidate / "backend" / "main.py").exists():
                hist = candidate / "eval_history"
                hist.mkdir(parents=True, exist_ok=True)
                print(f"  [bridge] eval_history -> {hist}")
                return hist

    # Legacy: dashboard inside project root
    for name in ["dashboard", "Deepeval_Foundry_dashboard", "Deepeval_Foundry_dashboard-main"]:
        candidate = PROJECT_ROOT / name
        if (candidate / "run.py").exists():
            hist = candidate / "eval_history"
            hist.mkdir(parents=True, exist_ok=True)
            return hist

    fallback = PROJECT_ROOT / "eval_history"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _make_llm_span(question: str, response: str, latency_s: float, model: str) -> dict:
    """Synthesize an llmSpan from latency data for the Tracer View."""
    lat = max(0.01, float(latency_s or 1.0))
    end = _dt.datetime.now(_dt.timezone.utc)
    start = end - _dt.timedelta(seconds=lat)
    return {
        "uuid":             str(_uuid.uuid4()),
        "name":             "llm-answer-generation",
        "type":             "llm",
        "status":           "OK",
        "startTime":        start.isoformat(),
        "endTime":          end.isoformat(),
        "model":            model,
        "provider":         "azure",
        "input":            question[:500],
        "output":           response[:500],
        "inputTokenCount":  None,
        "outputTokenCount": None,
        "costPerInputToken":  None,
        "costPerOutputToken": None,
        "metadata":         {"source": "ragas-eval"},
    }


def _make_chunking_span(contexts: list, chunk_size: int = 512) -> dict:
    """Synthesize a ToolSpan representing the chunking step."""
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
        "metadata":    {"chunk_size": chunk_size, "chunks_produced": len(contexts), "source": "ragas-eval"},
    }


def _make_reranking_span(contexts: list, top_k: int) -> dict:
    """Synthesize a ToolSpan representing the reranking/retrieval step."""
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
        "metadata":    {"top_k": top_k, "candidates": len(contexts), "source": "ragas-eval"},
    }


def _make_retriever_span(question: str, contexts: list, embedder: str = "text-embedding-ada-002") -> dict:
    """Synthesize a RetrieverSpan covering the full retrieval pipeline."""
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
        "retrievalContext": contexts[:top_k] if contexts else [],
        "metadata":  {
            "embedder":    embedder,
            "top_k":       top_k,
            "chunk_size":  512,
            "kb_source":   "playready-kb",
            "source":      "ragas-eval",
        },
    }


def _make_trace(case_name: str, question: str, response: str, latency_s: float,
                model: str, success: bool, contexts: list | None = None) -> dict:
    """Build a full trace with LLM + Retriever + Chunking + Reranking spans."""
    contexts = contexts or []
    llm_span      = _make_llm_span(question, response, latency_s, model)
    retriever_span = _make_retriever_span(question, contexts)
    chunking_span  = _make_chunking_span(contexts)
    reranking_span = _make_reranking_span(contexts, top_k=retriever_span["topK"])

    trace_start = retriever_span["startTime"]  # retrieval starts first
    trace_end   = llm_span["endTime"]

    return {
        "uuid":           str(_uuid.uuid4()),
        "name":           f"ragas/{case_name[:60]}",
        "status":         "OK" if success else "ERRORED",
        "startTime":      trace_start,
        "endTime":        trace_end,
        "input":          question[:500],
        "output":         response[:500],
        "metadata":       {"framework": "ragas"},
        "tags":           ["ragas"],
        "llmSpans":       [llm_span],
        "retrieverSpans": [retriever_span],
        "toolSpans":      [chunking_span, reranking_span],
        "agentSpans":     [],
        "baseSpans":      [],
        "metricsData":    [],
    }


# ── Metric name -> display name mapping ───────────────────────────────────────
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


# ── Real-trace normaliser ─────────────────────────────────────────────────────
# local_trace_exporter emits nested {spans:[...], children:[...]} trees with
# generic `type` values (task/tool/evaluator/agent). The dashboard's _parse_trace
# expects flat llmSpans/retrieverSpans/toolSpans/agentSpans/baseSpans buckets with
# DeepEval SpanType values (llm/retriever/tool/agent/base). Without converting,
# an attached real trace renders as an empty waterfall (all buckets default to []).

def _classify_real_span(node: dict) -> str:
    raw_type = (node.get("type") or "").lower()
    name = (node.get("name") or "").lower()
    if raw_type == "llm" or "llm" in name or "generation" in name:
        return "llm"
    if raw_type == "retriever" or any(k in name for k in ("retriev", "knowledge", "search", "lookup")):
        return "retriever"
    if raw_type == "agent":
        return "agent"
    if raw_type == "tool" or any(k in name for k in ("chunk", "rerank", "tool")):
        return "tool"
    return "base"


def _real_span_to_dashboard(node: dict, span_type: str, parent_uuid: str | None) -> dict:
    meta = dict(node.get("metadata") or {})
    status = (node.get("status") or "OK").upper()
    return {
        "uuid":             node.get("id") or str(_uuid.uuid4()),
        "name":             node.get("name"),
        "type":             span_type,
        "status":           "OK" if status != "ERROR" else "ERRORED",
        "parentUuid":       parent_uuid,
        "startTime":        node.get("startTime"),
        "endTime":          node.get("endTime"),
        "metadata":         meta,
        "input":            node.get("input"),
        "output":           node.get("output"),
        "error":            node.get("error"),
        "description":      meta.get("description") or (node.get("name") or "").replace("-", " ").replace("_", " ").title(),
        "embedder":         meta.get("embedder"),
        "topK":             meta.get("top_k") or meta.get("topK"),
        "chunkSize":        meta.get("chunk_size") or meta.get("chunkSize"),
        "model":            meta.get("model"),
        "provider":         meta.get("provider"),
        "inputTokenCount":  meta.get("input_token_count"),
        "outputTokenCount": meta.get("output_token_count"),
        "retrievalContext": meta.get("retrieval_context") or [],
    }


def _flatten_real_spans(node: dict, parent_uuid: str | None, buckets: dict[str, list]) -> None:
    for child in (node.get("spans") or node.get("children") or []):
        bucket = _classify_real_span(child)
        buckets[bucket].append(_real_span_to_dashboard(child, bucket, parent_uuid))
        _flatten_real_spans(child, child.get("id"), buckets)


def _convert_real_trace(real_trace: dict, fallback: dict | None) -> dict | None:
    """Normalise a local_trace_exporter trace tree into the dashboard's flat-bucket schema.

    Returns None (keep the synthesized trace) if the real trace has no usable spans.
    """
    root = None
    for candidate in (real_trace.get("traces") or [real_trace]):
        if isinstance(candidate, dict):
            root = candidate
            break
    if not root:
        return None

    buckets: dict[str, list] = {"llm": [], "retriever": [], "tool": [], "agent": [], "base": []}
    _flatten_real_spans(root, root.get("id"), buckets)
    if not any(buckets.values()):
        return None

    fallback = fallback or {}
    return {
        "uuid":           root.get("id") or fallback.get("uuid") or str(_uuid.uuid4()),
        "name":           fallback.get("name") or root.get("name"),
        "status":         root.get("status") or fallback.get("status") or "OK",
        "startTime":      root.get("startTime") or fallback.get("startTime"),
        "endTime":        root.get("endTime") or fallback.get("endTime"),
        "input":          root.get("input") if root.get("input") is not None else fallback.get("input"),
        "output":         root.get("output") if root.get("output") is not None else fallback.get("output"),
        "metadata":       {**(fallback.get("metadata") or {}), "source": "local-tracer"},
        "tags":           fallback.get("tags") or ["ragas"],
        "llmSpans":       buckets["llm"],
        "retrieverSpans": buckets["retriever"],
        "toolSpans":      buckets["tool"],
        "agentSpans":     buckets["agent"],
        "baseSpans":      buckets["base"],
        "metricsData":    [],
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

        latency  = row.get("latency_seconds")
        question = row.get("question") or ""
        response = row.get("response") or ""
        name     = row.get("id") or question[:60]
        contexts = row.get("retrieved_chunks") or []

        trace = _make_trace(
            case_name=name,
            question=question,
            response=response,
            latency_s=float(latency) if latency is not None else 1.5,
            model=eval_model,
            success=row_passed,
            contexts=contexts,
        )

        test_cases.append({
            "name":             name,
            "input":            question,
            "actualOutput":     response,
            "expectedOutput":   row.get("ground_truth") or None,
            "retrievalContext": row.get("retrieved_chunks") or [],
            "success":          row_passed,
            "metricsData":      metrics_data,
            "runDuration":      float(latency) if latency is not None else None,
            "evaluationCost":   0.0,
            "tags":             ["ragas"],
            "trace":            trace,
            "traces":           [trace],
        })

    # Override synthesized trace if local_trace_exporter produced a real one
    try:
        _pending = getattr(_T, "_pending_by_case", {}) or {}
        for _tc in test_cases:
            _key = str(_tc.get("name") or "")
            _real_trace = _pending.get(_key)
            if not _real_trace:
                _q = str(_tc.get("input") or "")
                for _k, _v in _pending.items():
                    if _k and _q and (_k in _q or _q[:60] in _k):
                        _real_trace = _v
                        break
            if _real_trace:
                _converted = _convert_real_trace(_real_trace, _tc.get("trace"))
                if _converted:
                    _tc["trace"]  = _converted
                    _tc["traces"] = [_converted]
    except Exception as _e:
        print(f"[trace] real-trace attach skipped: {_e}")

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
    """Convert RAGAs payload -> DeepEval test_run_*.json and save to eval_history/."""
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
            "project":      "playready",
            "framework":    "ragas",
            "model":        provider.get("model", "unknown"),
            "provider":     provider.get("provider", "unknown"),
            "environment":  os.getenv("ENVIRONMENT", "development"),
            "version":      os.getenv("APP_VERSION", ""),
            "bot_type":     os.getenv("BOT_TYPE", payload.get("bot_type", "public")),
            "metrics_profile": payload.get("metrics_profile", ""),
            "dataset_size": payload.get("dataset_size", 0),
        },
        "identifier": "ragas-eval",
    }

    dest = _find_eval_history()
    fname = dest / f"test_run_{int(time.time())}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(run, f, indent=2, ensure_ascii=False)

    print(f"  Dashboard: {passed} passed / {failed} failed -> {fname}")
    return fname
