"""
recover_dashboard.py
====================
Fixes 3 things in one run:
  1. Removes ALL .bak_* files in dashboard eval_history (they're stale and dangerous).
  2. Re-tags every test_run_*.json there with project='playready-foundry'.
  3. Moves any stray runs from the WRONG location into the dashboard folder.

Run:
    python recover_dashboard.py
"""
from __future__ import annotations
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASH_HIST = Path(r"C:\Users\v-snistane\tools\deepeval-dashboard\eval_history")
STRAY_HIST = ROOT / "eval_history"  # where new run accidentally landed
PROJECT_ID = "playready-foundry"


def banner(s: str) -> None:
    print("\n" + "=" * 70)
    print(s)
    print("=" * 70)


def step1_remove_stale_backups() -> int:
    banner("[1/4] Removing stale .bak_* files (they caused the regression)")
    n = 0
    for f in DASH_HIST.glob("*.bak_*"):
        f.unlink()
        print(f"  [DELETE] {f.name}")
        n += 1
    print(f"  Removed {n} backup file(s).")
    return n


def step2_move_stray_runs() -> int:
    banner(f"[2/4] Moving stray runs from {STRAY_HIST}")
    if not STRAY_HIST.exists():
        print("  No stray folder — skipping.")
        return 0
    n = 0
    for f in STRAY_HIST.glob("test_run_*.json"):
        target = DASH_HIST / f.name
        shutil.move(str(f), str(target))
        print(f"  [MOVE] {f.name}  ->  dashboard eval_history")
        n += 1
    # Remove empty folder
    try:
        STRAY_HIST.rmdir()
        print(f"  Removed empty folder: {STRAY_HIST}")
    except OSError:
        pass
    print(f"  Moved {n} stray run(s).")
    return n


def step3_retag_all_runs() -> int:
    banner(f"[3/4] Re-tagging every run with project='{PROJECT_ID}'")
    files = sorted(DASH_HIST.glob("test_run_*.json"))
    if not files:
        print(f"  [FAIL] No runs in {DASH_HIST}")
        return 0
    n_tagged = 0
    for f in files:
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [SKIP] {f.name}: {e}")
            continue
        hp = obj.setdefault("hyperparameters", {})
        if hp.get("project") == PROJECT_ID:
            print(f"  [OK]   {f.name}  (already tagged)")
            continue
        hp["project"] = PROJECT_ID
        f.write_text(json.dumps(obj, indent=2, ensure_ascii=False),
                     encoding="utf-8")
        print(f"  [TAG]  {f.name}")
        n_tagged += 1
    print(f"  Tagged {n_tagged}/{len(files)} run(s).")
    return n_tagged


def step4_verify() -> None:
    banner("[4/4] Verification")
    files = sorted(DASH_HIST.glob("test_run_*.json"))
    print(f"  Total runs in dashboard folder: {len(files)}")
    untagged = []
    for f in files:
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
            tag = obj.get("hyperparameters", {}).get("project")
            if tag != PROJECT_ID:
                untagged.append((f.name, tag))
        except Exception:
            untagged.append((f.name, "<unparseable>"))
    if untagged:
        print(f"  [WARN] {len(untagged)} run(s) NOT tagged correctly:")
        for name, tag in untagged:
            print(f"    - {name}  project={tag!r}")
    else:
        print(f"  [OK] All {len(files)} runs tagged '{PROJECT_ID}'")


def main() -> int:
    print("Dashboard recovery")
    print(f"Dashboard history : {DASH_HIST}")
    print(f"Stray history     : {STRAY_HIST}")

    if not DASH_HIST.exists():
        print(f"[FAIL] {DASH_HIST} does not exist")
        return 2

    step1_remove_stale_backups()
    step2_move_stray_runs()
    step3_retag_all_runs()
    step4_verify()

    print("\n" + "=" * 70)
    print("Now do EXACTLY this:")
    print("=" * 70)
    print("1. In the dashboard's terminal: Ctrl+C")
    print("2. In any PowerShell:")
    print('   $env:DEEPEVAL_RESULTS_FOLDER = "C:\\Users\\v-snistane\\tools\\deepeval-dashboard\\eval_history"')
    print("3. Then restart dashboard:")
    print("   cd C:\\Users\\v-snistane\\tools\\deepeval-dashboard")
    print("   python run.py")
    print("4. Hard-refresh browser (Ctrl+Shift+R)")
    print("5. 'default' card disappears, 'PlayReady Foundry RAG' shows 8 runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())