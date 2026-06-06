"""
apply_full_deep_tracing.py
==========================
Injects the _T tracer into all 5 pipeline files and wraps the right
functions with @_T.observe(...) so each test case produces a nested
trace tree visible in the dashboard's Trace Viewer.

Files touched:
  scripts/run_ragas_bridge.py
  scripts/query_new_agent.py
  ragas_layer/ragas_runner.py
  ragas_layer/dashboard_bridge.py
  foundry_layer/foundry_evaluator.py

Idempotent via __FULL_DEEP_TRACER_INJECTED__ marker.
"""
from __future__ import annotations
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MARKER = "# __FULL_DEEP_TRACER_INJECTED__"

IMPORT_BLOCK = '''# __FULL_DEEP_TRACER_INJECTED__
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
'''


# Per-file wrap rules.
# Each rule: (func_name, span_type, span_name)
WRAP_RULES: dict[str, list[tuple[str, str, str]]] = {
    "scripts/query_new_agent.py": [
        # The script-level entry plus likely sub-steps. Functions that don't exist
        # in your file are silently skipped, so this list is forgiving.
        ("query_new_agent",       "agent",     "foundry_agent_call"),
        ("query_agent",           "agent",     "foundry_agent_call"),
        ("main",                  "task",      "query_new_agent_main"),
        ("_call_agent",           "agent",     "foundry_agent_call"),
        ("_create_thread",        "tool",      "create_thread"),
        ("_post_message",         "tool",      "post_message"),
        ("_wait_for_run",         "tool",      "wait_for_run"),
        ("_get_agent_response",   "llm",       "generate_answer"),
        ("_extract_answer",       "llm",       "extract_answer"),
        ("_get_retrieved_chunks", "retriever", "retrieve_chunks"),
        ("_extract_chunks",       "retriever", "retrieve_chunks"),
        ("_collect_citations",    "tool",      "extract_citations"),
        ("_extract_citations",    "tool",      "extract_citations"),
    ],
    "ragas_layer/ragas_runner.py": [
        ("run_ragas_evaluation",  "task",      "ragas_run"),
        ("_execute_metric",       "evaluator", "ragas_metric"),
    ],
    "foundry_layer/foundry_evaluator.py": [
        ("run_all_foundry_evaluations",  "task",      "foundry_run"),
        ("run_foundry_quality_evaluation","evaluator","foundry_quality"),
        ("run_foundry_nlp_evaluation",   "evaluator", "foundry_nlp"),
        ("run_foundry_safety_evaluation","evaluator", "foundry_safety"),
        ("generate_foundry_report",      "task",      "foundry_report"),
    ],
    # No wrap rules needed for bridge / dashboard_bridge - just the import.
    "scripts/run_ragas_bridge.py": [],
    "ragas_layer/dashboard_bridge.py": [],
}


def patch_one(rel: str) -> bool:
    path = ROOT / rel
    if not path.exists():
        print(f"  [SKIP] {rel} not found")
        return False

    src = path.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"  [SKIP] {rel} already patched")
        return False

    # Backup
    bk = path.with_suffix(f".py.bak_{datetime.now():%Y%m%d_%H%M%S}")
    shutil.copy2(path, bk)

    # 1. Inject import block at the very top.
    new_src = IMPORT_BLOCK + "\n" + src

    # 2. Apply per-file wrap rules. We use regex on lines so we don't
    #    need a full AST rewrite.
    wrap_count = 0
    for func_name, span_type, span_name in WRAP_RULES.get(rel, []):
        # Match: "^(\s*)def <name>\("  with optional leading spaces.
        pattern = re.compile(
            rf"^(?P<indent>[ \t]*)def\s+{re.escape(func_name)}\s*\(",
            re.MULTILINE,
        )
        def repl(m: re.Match) -> str:
            indent = m.group("indent")
            deco = f'{indent}@_T.observe(type="{span_type}", name="{span_name}")\n'
            return deco + m.group(0)
        new_src, n = pattern.subn(repl, new_src, count=1)
        if n:
            wrap_count += 1
            print(f"    + decorated {func_name}  ({span_type}/{span_name})")

    # 3. Special hook: in ragas_runner.py, add set_case_key inside the
    #    per-row loop within run_ragas_evaluation. Anchor: "for base_row in rows:"
    if rel == "ragas_layer/ragas_runner.py":
        anchor = "    for base_row in rows:"
        new_src = new_src.replace(
            anchor,
            anchor + "\n        try:\n            _T.set_case_key(base_row.get(\"id\") or base_row.get(\"question\"))\n        except Exception:\n            pass",
            1,
        )

    # 4. Special hook: in dashboard_bridge.py, attach pending trace to each
    #    test case before write. Anchor: "    return test_cases"
    if rel == "ragas_layer/dashboard_bridge.py":
        anchor = "    return test_cases"
        injection = (
            "    # Attach per-case traces if local_trace_exporter is available.\n"
            "    try:\n"
            "        _pending = getattr(_T, \"_pending_by_case\", {}) or {}\n"
            "        for _tc in test_cases:\n"
            "            _key = str(_tc.get(\"name\") or \"\")\n"
            "            _trace = _pending.get(_key)\n"
            "            if not _trace:\n"
            "                _q = str(_tc.get(\"input\") or \"\")\n"
            "                for _k, _v in _pending.items():\n"
            "                    if _k and _q and (_k in _q or _q[:60] in _k):\n"
            "                        _trace = _v\n"
            "                        break\n"
            "            if _trace:\n"
            "                _tc[\"trace\"] = _trace\n"
            "                _tc[\"traces\"] = [_trace]\n"
            "    except Exception as _e:\n"
            "        print(f\"[trace] attach skipped: {_e}\")\n"
            "\n"
        )
        new_src = new_src.replace(anchor, injection + anchor, 1)

    path.write_text(new_src, encoding="utf-8")
    print(f"  [PATCH] {rel}   (backup: {bk.name}, wraps: {wrap_count})")
    return True


def main() -> int:
    print("Applying full deep tracing...")
    total = 0
    for rel in WRAP_RULES:
        if patch_one(rel):
            total += 1
    print(f"\nPatched {total} file(s).")
    print("\nNow re-run the bridge:")
    print('  $env:PYTHONPATH = "."')
    print("  python scripts\\run_ragas_bridge.py")
    print("Then hard-refresh dashboard -> Trace Viewer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
