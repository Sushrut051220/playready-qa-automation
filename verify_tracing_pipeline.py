"""
verify_tracing_pipeline.py
==========================
Answers 5 yes/no questions to pinpoint why Trace Viewer is empty:

  1. Is local_trace_exporter.py importable?
  2. Is the _T tracer working (not the no-op)?
  3. Did the WRAP_RULES decorators land in each pipeline file?
  4. Does the newest test_run_*.json contain trace/spans/durationMs fields?
  5. Are there any standalone trace_*.json files?
"""
from __future__ import annotations
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HIST = Path(os.getenv(
    "DEEPEVAL_RESULTS_FOLDER",
    r"C:\Users\v-snistane\tools\deepeval-dashboard\eval_history",
))


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# ---- 1) exporter import ----
section("[1] local_trace_exporter import")
try:
    from local_trace_exporter import get_tracer, LocalTracer
    t = get_tracer()
    print(f"  [OK] imported, get_tracer() returned {type(t).__name__}")
    print(f"       is LocalTracer? {isinstance(t, LocalTracer)}")
except Exception as e:
    print(f"  [FAIL] cannot import: {type(e).__name__}: {e}")

# ---- 2) tracer actually emits ----
section("[2] tracer end-to-end smoke test")
try:
    from local_trace_exporter import get_tracer
    tr = get_tracer()
    tr.set_case_key("smoke_test_case")
    with tr.span("smoke_root", type="task", input="hi") as s:
        with tr.span("smoke_child", type="tool") as c:
            c.output = "world"
        s.output = "ok"
    # check if a file landed
    files = sorted(HIST.glob("trace_*.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    print(f"  Standalone trace files in eval_history: {len(files)}")
    if files:
        print(f"  Newest: {files[0].name} ({files[0].stat().st_size} bytes)")
except Exception as e:
    print(f"  [FAIL] smoke test crashed: {type(e).__name__}: {e}")

# ---- 3) marker check on each pipeline file ----
section("[3] Pipeline files - injection markers present?")
PIPELINE = [
    "scripts/run_ragas_bridge.py",
    "scripts/query_new_agent.py",
    "ragas_layer/ragas_runner.py",
    "ragas_layer/dashboard_bridge.py",
    "foundry_layer/foundry_evaluator.py",
]
for rel in PIPELINE:
    p = ROOT / rel
    if not p.exists():
        print(f"  [MISSING] {rel}")
        continue
    src = p.read_text(encoding="utf-8", errors="ignore")
    has_inject = "__FULL_DEEP_TRACER_INJECTED__" in src
    decos      = len(re.findall(r"@_T\.observe\(", src))
    set_case   = "_T.set_case_key" in src
    attach     = "_pending_by_case" in src
    print(f"  {rel}")
    print(f"     marker={has_inject}  @_T.observe count={decos}  set_case_key={set_case}  trace-attach={attach}")

# ---- 4) newest test_run check ----
section("[4] Newest test_run_*.json - does it have trace fields?")
runs = sorted(HIST.glob("test_run_*.json"),
              key=lambda p: p.stat().st_mtime, reverse=True)
if not runs:
    print(f"  [FAIL] no runs in {HIST}")
else:
    latest = runs[0]
    print(f"  File: {latest.name} ({latest.stat().st_size:,} bytes)")
    raw = latest.read_text(encoding="utf-8", errors="ignore")
    print(f'  contains "trace":    {raw.count(chr(34) + "trace" + chr(34) + ":")}x')
    print(f'  contains "traces":   {raw.count(chr(34) + "traces" + chr(34) + ":")}x')
    print(f'  contains "spans":    {raw.count(chr(34) + "spans" + chr(34) + ":")}x')
    print(f'  contains "durationMs": {raw.count(chr(34) + "durationMs" + chr(34) + ":")}x')
    try:
        data = json.loads(raw)
        tcs = data.get("testCases", [])
        if tcs:
            tc0 = tcs[0]
            print(f"  testCases[0] keys: {list(tc0.keys())}")
            if "trace" in tc0:
                tr = tc0["trace"]
                print(f"  testCases[0].trace.name: {tr.get('name')}")
                print(f"  testCases[0].trace.spans count: {len(tr.get('spans', []))}")
    except Exception as e:
        print(f"  [WARN] cannot parse JSON: {e}")

# ---- 5) summary ----
section("[5] Summary")
print("If [1] failed: local_trace_exporter.py is missing/broken -> traces can't be created.")
print("If [2] created a standalone trace file: tracer works but dashboard ignores standalone files.")
print("If [3] shows decos=0 on the bridge/runner: decorators never landed on real functions.")
print("If [4] shows 0 trace/spans fields: dashboard_bridge attach hook didn't trigger.")
