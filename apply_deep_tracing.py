"""
apply_deep_tracing.py
=====================
Adds nested span tracing to the RAGAS bridge + foundry caller using the
local_trace_exporter (writes one trace JSON file per bridge run).

Idempotent and safe.
"""
from __future__ import annotations
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TARGETS = {
    ROOT / "scripts" / "run_ragas_bridge.py": "bridge",
    ROOT / "foundry_layer" / "foundry_evaluator.py": "foundry",
}

MARKER = "# __DEEP_TRACER_INJECTED__"

IMPORT = '''# __DEEP_TRACER_INJECTED__
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
'''


def patch_file(path: Path, role: str) -> bool:
    if not path.exists():
        print(f"  [SKIP] {path.relative_to(ROOT)} not found")
        return False
    src = path.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"  [SKIP] {path.relative_to(ROOT)} already patched")
        return False
    bk = path.with_suffix(f".py.bak_{datetime.now():%Y%m%d_%H%M%S}")
    shutil.copy2(path, bk)
    path.write_text(IMPORT + "\n" + src, encoding="utf-8")
    print(f"  [PATCH] {path.relative_to(ROOT)} (backup: {bk.name})")
    return True


def append_bridge_wrapper(path: Path) -> None:
    """Wrap the bridge's main entry in a tracer span if not already."""
    src = path.read_text(encoding="utf-8")
    if "_T.span(\"ragas_bridge_run\"" in src:
        return
    snippet = '''

# Auto-injected wrapper: emit a top-level trace per bridge invocation.
def _traced_bridge_entry_main():
    with _T.span("ragas_bridge_run", type="task",
                 input={"script": __file__},
                 metadata={"project": "playready-foundry"}):
        return _orig_main() if "_orig_main" in globals() else None
'''
    # Simple approach: just append the snippet so it can be called manually if desired.
    # For non-invasive activation, we rely on the foundry caller being wrapped instead.
    path.write_text(src + snippet, encoding="utf-8")


def main() -> int:
    n = 0
    for p, role in TARGETS.items():
        if patch_file(p, role):
            n += 1
    print(f"\nPatched {n}/{len(TARGETS)} file(s).")
    print("Next:")
    print("  1) Manually wrap your foundry agent call. Example:")
    print("       @_T.observe(type=\"agent\", name=\"query_foundry_agent\")")
    print("       def query_foundry_agent(...): ...")
    print("  2) Re-run the bridge.")
    print("  3) Check eval_history for trace_*.json files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
