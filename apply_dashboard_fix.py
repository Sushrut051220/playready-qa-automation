"""
apply_dashboard_fix.py
======================
One-shot patcher for the 'empty metricsData' bug in dashboard_bridge handoff.

Bug:
    ragas_runner.py looks up per-row metric scores by matching `r.get("question")`,
    but its own column normalization renames `question` -> `user_input`. So the
    match always fails, every score becomes None, every result becomes "SKIPPED",
    and dashboard_bridge writes `metricsData: []` for every test case.

Fix:
    Replace the matcher with one that tries:
        id == row_id  OR  user_input == question  OR  question == question

Safe-by-default:
    - Backs up ragas_runner.py to ragas_runner.py.bak before patching.
    - Idempotent: if the file is already patched, it does nothing.
    - Verifies the change actually landed before exiting.

Run:
    python apply_dashboard_fix.py
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET_FILE = Path(__file__).resolve().parent / "ragas_layer" / "ragas_runner.py"

# Exact buggy block (whitespace-tolerant via .strip() comparison line-by-line)
OLD_BLOCK = '''        for metric_name, threshold in payload["thresholds"].items():
            match = next(
                (
                    r for r in payload["metric_details"].get(metric_name, [])
                    if r.get("id") == row_id or r.get("question") == base_row.get("question")
                ),
                None,
            )'''

NEW_BLOCK = '''        for metric_name, threshold in payload["thresholds"].items():
            base_question = base_row.get("question") or base_row.get("user_input")
            match = next(
                (
                    r for r in payload["metric_details"].get(metric_name, [])
                    if (
                        (row_id is not None and r.get("id") == row_id)
                        or (base_question and r.get("user_input") == base_question)
                        or (base_question and r.get("question") == base_question)
                    )
                ),
                None,
            )'''

# Marker that proves the patch is already applied
PATCH_MARKER = "base_question = base_row.get(\"question\") or base_row.get(\"user_input\")"


def main() -> int:
    print("=" * 70)
    print("Dashboard 'empty metricsData' patcher")
    print("=" * 70)

    if not TARGET_FILE.exists():
        print(f"[FAIL] Target file not found:\n  {TARGET_FILE}")
        return 2

    original = TARGET_FILE.read_text(encoding="utf-8")
    print(f"[OK]   Loaded: {TARGET_FILE}  ({len(original):,} chars)")

    # Idempotency check
    if PATCH_MARKER in original:
        print("[SKIP] Patch already applied. Nothing to do.")
        return 0

    if OLD_BLOCK not in original:
        print("[FAIL] Could not find the expected buggy block.")
        print("       The file may have been edited manually or by a different version.")
        print("       Please share the contents of:")
        print("       ragas_layer/ragas_runner.py  (lines ~540-585)")
        return 3

    # Backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = TARGET_FILE.with_suffix(f".py.bak_{timestamp}")
    shutil.copy2(TARGET_FILE, backup_path)
    print(f"[OK]   Backup created: {backup_path.name}")

    # Patch
    patched = original.replace(OLD_BLOCK, NEW_BLOCK, 1)
    if patched == original:
        print("[FAIL] str.replace did not change anything. Aborting without write.")
        return 4

    TARGET_FILE.write_text(patched, encoding="utf-8")
    print(f"[OK]   File patched: {TARGET_FILE.name}")

    # Verify
    verify = TARGET_FILE.read_text(encoding="utf-8")
    if PATCH_MARKER not in verify:
        print("[FAIL] Verification failed: marker not found after write.")
        return 5

    print("[OK]   Verification passed — patch marker present.")
    print()
    print("Next steps:")
    print("  1) Re-run the bridge:")
    print("     $env:PYTHONPATH = \".\"")
    print("     .venv\\Scripts\\python.exe scripts\\run_ragas_bridge.py")
    print()
    print("  2) Verify with:")
    print("     .venv\\Scripts\\python.exe verify_dashboard_fix.py")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())