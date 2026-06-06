"""
backfill_project_tag.py
=======================
Tags every existing test_run_*.json in the dashboard's eval_history with
hyperparameters.project = 'playready-foundry'.

Run:
    python backfill_project_tag.py
"""
from __future__ import annotations
import json, os, shutil, sys
from datetime import datetime
from pathlib import Path

HIST = Path(os.getenv(
    "DEEPEVAL_RESULTS_FOLDER",
    r"C:\Users\v-snistane\tools\deepeval-dashboard\eval_history",
))
PROJECT_ID = "playready-foundry"


def main() -> int:
    print(f"History folder: {HIST}")
    print(f"Project tag   : {PROJECT_ID}\n")

    if not HIST.exists():
        print(f"[FAIL] {HIST} does not exist")
        return 2

    files = sorted(HIST.glob("test_run_*.json"))
    if not files:
        print("[FAIL] No test_run_*.json files found.")
        return 3

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tagged = skipped = 0

    for f in files:
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [SKIP] {f.name}: {e}")
            skipped += 1
            continue

        hp = obj.setdefault("hyperparameters", {})
        if hp.get("project") == PROJECT_ID:
            print(f"  [OK]   {f.name}  (already tagged)")
            continue

        bk = f.with_suffix(f".json.bak_{ts}")
        if not bk.exists():
            shutil.copy2(f, bk)
        hp["project"] = PROJECT_ID
        f.write_text(json.dumps(obj, indent=2, ensure_ascii=False),
                     encoding="utf-8")
        print(f"  [TAG]  {f.name}")
        tagged += 1

    print(f"\nTagged: {tagged}   Skipped: {skipped}   Total: {len(files)}")
    print("\nHard-refresh the dashboard (Ctrl+Shift+R).")
    print("'PlayReady Foundry RAG' card should appear with your 7 runs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())