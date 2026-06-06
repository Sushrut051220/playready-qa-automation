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

# __DEEP_TRACER_INJECTED__
try:
    from local_trace_exporter import get_tracer as _get_tracer
    _T = _get_tracer()
except Exception:
    class _Noop:
        from contextlib import contextmanager
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
    _T = _Noop()

# __PATCH_OBSERVE_TRACING__
# Auto-injected: deepeval tracing for the dashboard's Trace Viewer.
try:
    from deepeval.tracing import observe, update_current_span
    _TRACING_ENABLED = True
except Exception as _e:
    _TRACING_ENABLED = False
    def observe(*args, **kwargs):
        def _wrap(fn):
            return fn
        return _wrap
    def update_current_span(*args, **kwargs):
        pass

"""Run RAGAS evaluation directly on the bridge dataset (data/ragas_eval_dataset.json)."""

import json
import os
from pathlib import Path

from datasets import Dataset
from ragas_layer.ragas_runner import run_ragas_evaluation

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_DATASET = PROJECT_ROOT / "data" / "ragas_eval_dataset.json"
RAGAS_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "ragas"

os.environ.setdefault("RAGAS_METRICS_PROFILE", "full")

rows = json.loads(BRIDGE_DATASET.read_text(encoding="utf-8"))
ds = Dataset.from_list(rows)
print(f"Dataset: {ds.num_rows} rows | columns: {ds.column_names}")

results = run_ragas_evaluation(ds, output_dir=str(RAGAS_OUTPUT_DIR))

print("\n=== EXECUTED METRICS ===")
for m in results.get("executed_metrics", []):
    score = results.get("summary", {}).get(m)
    print(f"  + {m}: {score}")

print("\n=== SKIPPED METRICS ===")
for s in results.get("skipped_metrics", []):
    print(f"  - {s['metric']}: {s['reason']}")

print(f"\nResults saved to: {RAGAS_OUTPUT_DIR / 'ragas_results.json'}")


@observe(name="ragas_evaluate_row", type="task")
def _traced_evaluate_row(row_index, row_dict, evaluate_fn):
    """Wrap one row's RAGAS evaluation so Trace Viewer captures it."""
    try:
        update_current_span(
            input=row_dict.get("question") or row_dict.get("user_input"),
            metadata={
                "row_index":   row_index,
                "test_suite":  row_dict.get("source_test_suite"),
                "query_type":  row_dict.get("query_type"),
                "test_id":     row_dict.get("id"),
            },
        )
    except Exception:
        pass
    result = evaluate_fn(row_dict)
    try:
        update_current_span(output=result)
    except Exception:
        pass
    return result
