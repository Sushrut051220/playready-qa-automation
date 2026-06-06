"""
diagnose_dashboard_display.py
=============================
Investigates why the dashboard UI doesn't show a run that IS in eval_history.

Checks:
    1. Dashboard process running?
    2. Latest JSON file present and valid?
    3. Where does the dashboard read from? (run.py + backend/config.py)
    4. Does that path match the eval_history we are writing to?
    5. Does the JSON shape match what the dashboard expects?

Run:
    python diagnose_dashboard_display.py
"""

from __future__ import annotations
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASH = ROOT / "Deepeval_Foundry_dashboard-main"
HIST = DASH / "eval_history"


def banner(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def main() -> int:
    banner("1. Latest dashboard JSON")
    if not HIST.exists():
        print(f"   [FAIL] {HIST} does not exist")
        return 2
    files = sorted(HIST.glob("test_run_*.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print(f"   [FAIL] No test_run_*.json in {HIST}")
        return 3
    latest = files[0]
    print(f"   File: {latest.name}")
    print(f"   Size: {latest.stat().st_size:,} bytes")
    print(f"   mtime: {latest.stat().st_mtime}")
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
        keys = list(data.keys())
        print(f"   Top-level keys: {keys[:12]}{' ...' if len(keys) > 12 else ''}")
        tc = data.get("testCases", [])
        ms = data.get("metricsScores", [])
        print(f"   testCases: {len(tc)}  metricsScores: {len(ms)}")
        if tc:
            first_md = tc[0].get("metricsData", [])
            print(f"   testCases[0].metricsData: {len(first_md)}")
        # All recent runs at a glance
        print(f"\n   Recent runs ({min(len(files), 5)}):")
        for f in files[:5]:
            sz = f.stat().st_size
            print(f"     - {f.name}  {sz:,} bytes")
    except Exception as e:
        print(f"   [FAIL] Could not parse JSON: {e}")
        return 4

    banner("2. Where dashboard reads from")
    candidates = list(DASH.rglob("*.py"))
    candidates = [p for p in candidates if "__pycache__" not in p.parts]
    pattern = re.compile(r"eval_history|DEEPEVAL_RESULTS_FOLDER|test_run_", re.I)
    hits = []
    for f in candidates:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            if pattern.search(line):
                hits.append((f.relative_to(DASH), lineno, line.strip()[:140]))
    if not hits:
        print("   [WARN] No references found in dashboard Python files")
    else:
        for rel, ln, txt in hits:
            print(f"   {rel}:{ln}  {txt}")

    banner("3. Running processes")
    try:
        if os.name == "nt":
            out = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                text=True, errors="ignore"
            )
            print(out.strip() or "   (no python.exe)")
        else:
            out = subprocess.check_output(["ps", "-ef"], text=True)
            print("\n".join(l for l in out.splitlines()
                            if "streamlit" in l or "uvicorn" in l or "run.py" in l)
                  or "   (no dashboard process)")
    except Exception as e:
        print(f"   [WARN] Could not list processes: {e}")

    banner("4. Ports in use (8501 Streamlit / 5000 Flask / 8000 FastAPI)")
    try:
        if os.name == "nt":
            out = subprocess.check_output(
                ["netstat", "-ano"], text=True, errors="ignore"
            )
            for line in out.splitlines():
                if any(p in line for p in (":8501 ", ":5000 ", ":8000 ", ":3000 ")):
                    if "LISTENING" in line:
                        print(f"   {line.strip()}")
        else:
            out = subprocess.check_output(["lsof", "-iTCP", "-sTCP:LISTEN"], text=True)
            for line in out.splitlines():
                if any(p in line for p in (":8501", ":5000", ":8000", ":3000")):
                    print(f"   {line.strip()}")
    except Exception as e:
        print(f"   [WARN] Could not probe ports: {e}")

    banner("5. Recommendation")
    print("   - If section 3 shows NO dashboard process, run:")
    print("       python restart_dashboard.py")
    print("   - If section 2 shows a path != Deepeval_Foundry_dashboard-main/eval_history,")
    print("     set the env var first:")
    print("       $env:DEEPEVAL_RESULTS_FOLDER = " +
          f'"{HIST}"')
    print("   - If section 1 shows metricsData populated and section 3 shows the")
    print("     dashboard running, do a HARD REFRESH in the browser (Ctrl + F5).")
    print("   - If even after a hard refresh the run is missing from the run list,")
    print("     send the output of THIS script back to chat — it likely means the")
    print("     dashboard schema needs one more JSON field.")
    return 0


if __name__ == "__main__":
    sys.exit(main())