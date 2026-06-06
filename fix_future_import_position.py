"""
fix_future_import_position.py
=============================
Python requires `from __future__ import ...` to be the very first statement
(after optional docstring/comments) in a module. My earlier patch prepended
the `_T` tracer block above the existing __future__ line, which broke imports.

This script:
  1. Finds every .py we touched (or all .py if --all).
  2. If a __future__ import exists after the file's first line, moves it
     to the very top.
  3. Leaves the rest of the file untouched.
  4. Backs up each file before modifying.
"""
from __future__ import annotations
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TARGETS = [
    ROOT / "scripts" / "run_ragas_bridge.py",
    ROOT / "scripts" / "query_new_agent.py",
    ROOT / "ragas_layer" / "ragas_runner.py",
    ROOT / "ragas_layer" / "dashboard_bridge.py",
    ROOT / "foundry_layer" / "foundry_evaluator.py",
]

# Capture ALL future imports (some files may import multiple symbols)
FUT = re.compile(r"^\s*from\s+__future__\s+import\s+[^\n]+\s*$", re.MULTILINE)


def fix_file(path: Path) -> bool:
    if not path.exists():
        print(f"  [SKIP] {path.name} not found")
        return False

    src = path.read_text(encoding="utf-8")
    matches = list(FUT.finditer(src))
    if not matches:
        print(f"  [OK]   {path.name} has no __future__ import")
        return False

    # Pull every __future__ line out and dedupe.
    fut_lines = []
    for m in matches:
        line = m.group(0).strip()
        if line not in fut_lines:
            fut_lines.append(line)

    # Strip them from the body.
    body = FUT.sub("", src)
    # Collapse any leftover empty lines at the very top.
    body = body.lstrip("\n")

    # Optional: keep a leading module docstring or shebang at the top of file
    # (rare here, but harmless to preserve). For our pipeline files there is
    # no shebang, so we'll just put __future__ at the very top.

    new_src = "\n".join(fut_lines) + "\n" + body

    if new_src == src:
        print(f"  [OK]   {path.name} already in correct position")
        return False

    bk = path.with_suffix(f".py.bak_{datetime.now():%Y%m%d_%H%M%S}")
    shutil.copy2(path, bk)
    path.write_text(new_src, encoding="utf-8")
    print(f"  [FIX]  {path.name}   (backup: {bk.name})")
    return True


def main() -> int:
    print("Fixing __future__ import positions...")
    n = sum(1 for p in TARGETS if fix_file(p))
    print(f"\nFixed {n}/{len(TARGETS)} file(s).")
    print("\nNow try the bridge again:")
    print('  $env:PYTHONPATH = "."')
    print("  python scripts\\run_ragas_bridge.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
