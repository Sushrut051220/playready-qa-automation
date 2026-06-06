"""
restart_dashboard.py
====================
Why your dashboard doesn't show the run:
    The dashboard JSON IS being written correctly to
    Deepeval_Foundry_dashboard-main/eval_history/test_run_<ts>.json
    with 11 populated metrics — but the dashboard server may not be running,
    or it's running stale (file watcher missed the update).

What this script does:
    1. Detects the dashboard's run.py
    2. Sets DEEPEVAL_RESULTS_FOLDER to the eval_history path it scans
    3. Starts the dashboard in a fresh subprocess
    4. Prints the URL to open

Run:
    python restart_dashboard.py
"""

from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASHBOARD_DIR = ROOT / "Deepeval_Foundry_dashboard-main"
EVAL_HISTORY = DASHBOARD_DIR / "eval_history"
RUN_PY = DASHBOARD_DIR / "run.py"


def main() -> int:
    print("=" * 70)
    print("Dashboard restarter")
    print("=" * 70)

    if not DASHBOARD_DIR.exists():
        print(f"[FAIL] Dashboard folder not found: {DASHBOARD_DIR}")
        return 2
    if not RUN_PY.exists():
        print(f"[FAIL] run.py not found: {RUN_PY}")
        print("       Check the dashboard project layout.")
        return 3

    EVAL_HISTORY.mkdir(parents=True, exist_ok=True)

    # Confirm there is at least one run JSON
    runs = sorted(EVAL_HISTORY.glob("test_run_*.json"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        print(f"[WARN] No test_run_*.json in {EVAL_HISTORY}")
        print("       Run scripts/run_ragas_bridge.py first.")
    else:
        latest = runs[0]
        print(f"[OK] Latest run JSON: {latest.name}  ({latest.stat().st_size:,} bytes)")

    env = os.environ.copy()
    env["DEEPEVAL_RESULTS_FOLDER"] = str(EVAL_HISTORY)
    env["PYTHONUNBUFFERED"] = "1"

    print(f"[OK] DEEPEVAL_RESULTS_FOLDER -> {EVAL_HISTORY}")
    print(f"[OK] Launching dashboard from: {DASHBOARD_DIR}")
    print("\n--- Dashboard output below (Ctrl+C to stop) ---\n")

    try:
        subprocess.run(
            [sys.executable, str(RUN_PY)],
            cwd=str(DASHBOARD_DIR),
            env=env,
            check=False,
        )
    except KeyboardInterrupt:
        print("\n[OK] Dashboard stopped by user.")
    return 0


if __name__ == "__main__":
    sys.exit(main())