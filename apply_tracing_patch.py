"""
apply_tracing_patch.py
======================
Adds defensive @observe tracing to scripts/run_ragas_bridge.py.
Idempotent and safe: if deepeval is missing or broken, RAGAS still works.
"""
from __future__ import annotations
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "scripts" / "run_ragas_bridge.py"
PATCH_MARKER = "# __PATCH_OBSERVE_TRACING__"

INJECTION = '''# __PATCH_OBSERVE_TRACING__
# Auto-injected: deepeval tracing for the dashboard's Trace Viewer.
# Defensive: if deepeval isn't available, observe is a no-op.
try:
    from deepeval.tracing import observe, update_current_span
    _TRACING_ENABLED = True
except Exception:
    _TRACING_ENABLED = False
    def observe(*args, **kwargs):
        def _wrap(fn):
            return fn
        return _wrap
    def update_current_span(*args, **kwargs):
        pass


@observe(name="ragas_bridge_run", type="task")
def _ragas_bridge_traced_entry(meta):
    try:
        update_current_span(input=meta.get("input"), metadata=meta.get("metadata", {}))
    except Exception:
        pass
'''


def main() -> int:
    if not TARGET.exists():
        print(f"[FAIL] Not found: {TARGET}")
        return 2
    src = TARGET.read_text(encoding="utf-8")
    if PATCH_MARKER in src:
        print("[SKIP] Already patched.")
        return 0
    bk = TARGET.with_suffix(f".py.bak_{datetime.now():%Y%m%d_%H%M%S}")
    shutil.copy2(TARGET, bk)
    print(f"[OK] Backup: {bk.name}")
    TARGET.write_text(INJECTION + "\n\n" + src, encoding="utf-8")
    print(f"[OK] Patched: {TARGET.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
