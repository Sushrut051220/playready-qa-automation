"""
verify_dashboard_fix.py
========================
Reads the LATEST test_run_*.json from Deepeval_Foundry_dashboard-main/eval_history/
and prints a quick health check so you can confirm metricsData is now populated.

Run AFTER re-running scripts/run_ragas_bridge.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
EVAL_HISTORY = PROJECT_ROOT / "Deepeval_Foundry_dashboard-main" / "eval_history"


def main() -> int:
    if not EVAL_HISTORY.exists():
        print(f"[FAIL] eval_history folder not found:\n  {EVAL_HISTORY}")
        return 2

    files = sorted(
        EVAL_HISTORY.glob("test_run_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        print(f"[FAIL] No test_run_*.json files in {EVAL_HISTORY}")
        return 3

    latest = files[0]
    print(f"[OK]   Latest dashboard JSON: {latest.name}")
    print(f"       Size: {latest.stat().st_size:,} bytes")

    data = json.loads(latest.read_text(encoding="utf-8"))
    test_cases = data.get("testCases", [])
    metrics_scores = data.get("metricsScores", [])

    print(f"       testPassed     : {data.get('testPassed')}")
    print(f"       testFailed     : {data.get('testFailed')}")
    print(f"       testCases      : {len(test_cases)}")
    print(f"       metricsScores  : {len(metrics_scores)}")

    if not test_cases:
        print("[FAIL] No test cases in JSON.")
        return 4

    first = test_cases[0]
    metrics_data = first.get("metricsData", [])
    print()
    print(f"First test case: {first.get('name')}")
    print(f"  metricsData count: {len(metrics_data)}")

    if not metrics_data:
        print("  [FAIL] metricsData is STILL EMPTY — fix did not take effect.")
        print("         Possible causes:")
        print("           - You didn't re-run scripts/run_ragas_bridge.py after patching")
        print("           - apply_dashboard_fix.py reported SKIP/FAIL")
        print("           - All metrics scored None (real failure, unrelated)")
        return 5

    print("  [OK]   metricsData populated. Sample metrics:")
    print()
    print(f"  {'metric':<32} {'score':>10}  {'success':>8}")
    print(f"  {'-'*32} {'-'*10}  {'-'*8}")
    for m in metrics_data[:15]:
        name = str(m.get("name", ""))[:32]
        score = m.get("score")
        success = m.get("success")
        score_str = f"{score:.4f}" if isinstance(score, (int, float)) else "n/a"
        print(f"  {name:<32} {score_str:>10}  {str(success):>8}")

    print()
    print("[OK]   Dashboard should now display this run with full metric scores.")
    print(f"       Reload your dashboard in the browser and look for run id from:")
    print(f"       {latest.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())