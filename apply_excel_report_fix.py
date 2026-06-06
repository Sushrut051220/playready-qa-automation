"""
apply_excel_report_fix.py
=========================
Fixes:
    1. NameError: name 'rows' is not defined        in _generate_bridge_excel_report
    2. NameError: name 'source_test_suite' ...      in same function

Strategy:
    Inject a 'rows = all_evaluator_rows' alias + source_test_suite derivation
    immediately AFTER the line 'all_evaluator_rows = list(question_row_map.values())'
    so all downstream code (KPI section, summary_rows, metric_explanations) works.

Safe-by-default:
    - Backs up audit/reporting.py before patching.
    - Idempotent via PATCH_MARKER.
    - Verifies the change landed before exit.

Run:
    python apply_excel_report_fix.py
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "audit" / "reporting.py"

ANCHOR = "    all_evaluator_rows = list(question_row_map.values())"

PATCH_MARKER = "# __PATCH_EXCEL_ROWS_ALIAS__"

INJECTION = '''

    # __PATCH_EXCEL_ROWS_ALIAS__
    # Auto-injected alias so the KPI / summary / metric_explanations sections work.
    # `rows` was referenced 11 times in this function but never assigned.
    # `all_evaluator_rows` (built above) has the exact shape they expect:
    #   id, question, response, ground_truth, retrieved_chunks, citations,
    #   citation_quotes, plus per-metric score columns.
    rows = all_evaluator_rows

    # Enrich `rows` with latency / token / citation info from the bridge dataset
    # (keyed by question) so KPI averages aren't all zero.
    _bridge_by_q = {
        str(_it.get("question") or _it.get("user_input") or "").strip(): _it
        for _it in bridge_dataset_rows
        if isinstance(_it, dict)
    }
    for _r in rows:
        _q = str(_r.get("question") or "").strip()
        _src = _bridge_by_q.get(_q, {}) if _q else {}
        if "latency_seconds" not in _r:
            _r["latency_seconds"] = _src.get("latency_seconds")
        if "total_tokens" not in _r:
            _tu = _src.get("token_usage") or {}
            _r["total_tokens"] = _tu.get("total_tokens") if isinstance(_tu, dict) else None
        # Make sure 'citations' is a non-empty-aware truthy/falsey value
        if _r.get("citations") is None:
            _r["citations"] = ""

    # `source_test_suite` is referenced in the KPI section. Derive from the
    # first bridge dataset row if available; otherwise from ragas_payload.
    try:
        source_test_suite
    except NameError:
        _src_suite = ""
        if bridge_dataset_rows and isinstance(bridge_dataset_rows[0], dict):
            _src_suite = str(bridge_dataset_rows[0].get("source_test_suite") or "")
        if not _src_suite and isinstance(ragas_payload, dict):
            _src_suite = str(ragas_payload.get("source_test_suite") or "")
        source_test_suite = _src_suite or "bridge_run"
'''


def main() -> int:
    print("=" * 70)
    print("Bridge Excel report patcher (rows + source_test_suite)")
    print("=" * 70)

    if not TARGET.exists():
        print(f"[FAIL] Not found: {TARGET}")
        return 2

    src = TARGET.read_text(encoding="utf-8")
    print(f"[OK]   Loaded: {TARGET.name}  ({len(src):,} chars)")

    if PATCH_MARKER in src:
        print("[SKIP] Patch already applied.")
        return 0

    if ANCHOR not in src:
        print(f"[FAIL] Anchor line not found:\n  {ANCHOR}")
        print("       File may have been edited. Send the function source to chat.")
        return 3

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_suffix(f".py.bak_{ts}")
    shutil.copy2(TARGET, backup)
    print(f"[OK]   Backup: {backup.name}")

    # Insert AFTER the anchor line (and any blank line that follows it)
    new_src = src.replace(ANCHOR, ANCHOR + INJECTION, 1)
    if new_src == src:
        print("[FAIL] str.replace did not modify the file.")
        return 4

    TARGET.write_text(new_src, encoding="utf-8")
    print(f"[OK]   Patched: {TARGET.name}")

    verify = TARGET.read_text(encoding="utf-8")
    if PATCH_MARKER not in verify:
        print("[FAIL] Verification failed: marker missing after write.")
        return 5

    print("[OK]   Verification passed.")
    print()
    print("Next steps:")
    print('  $env:PYTHONPATH = "."')
    print("  .venv\\Scripts\\python.exe scripts\\run_ragas_bridge.py")
    print()
    print("Then check the Excel report was created:")
    print("  Get-ChildItem .\\reports\\bridge\\Bridge_Evaluation_Report.xlsx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
