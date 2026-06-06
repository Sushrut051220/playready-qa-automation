"""
fix_and_start_dashboard.py
==========================
1. Installs python-multipart (FastAPI form-upload dependency the dashboard needs).
2. Kills any stale dashboard process holding port 5000.
3. Starts the dashboard fresh with DEEPEVAL_RESULTS_FOLDER set.

Run:
    python fix_and_start_dashboard.py
"""

from __future__ import annotations
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASH = ROOT / "Deepeval_Foundry_dashboard-main"
HIST = DASH / "eval_history"
RUN_PY = DASH / "run.py"


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, **kw)


def install_missing_packages() -> None:
    print("\n[1/3] Installing missing dashboard dependencies...")
    pkgs = [
        "python-multipart",      # the one that crashed
        "fastapi",
        "uvicorn[standard]",
        "watchdog",              # file watcher used by backend/services/file_watcher.py
        "pydantic",
    ]
    run([sys.executable, "-m", "pip", "install", "-U", *pkgs])


def kill_port(port: int) -> None:
    print(f"\n[2/3] Freeing port {port}...")
    if os.name != "nt":
        return
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, errors="ignore")
    except Exception:
        return
    pids = set()
    for line in out.splitlines():
        if f":{port} " in line and "LISTENING" in line:
            parts = line.split()
            if parts:
                pids.add(parts[-1])
    for pid in pids:
        print(f"  Killing PID {pid}")
        try:
            subprocess.run(["taskkill", "/F", "/PID", pid],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"  [WARN] taskkill failed: {e}")
    time.sleep(1)


def start_dashboard() -> int:
    print("\n[3/3] Starting dashboard...")
    if not RUN_PY.exists():
        print(f"[FAIL] {RUN_PY} not found")
        return 2

    HIST.mkdir(parents=True, exist_ok=True)
    runs = sorted(HIST.glob("test_run_*.json"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    if runs:
        print(f"  Latest run JSON ready: {runs[0].name}")

    env = os.environ.copy()
    env["DEEPEVAL_RESULTS_FOLDER"] = str(HIST)
    env["PYTHONUNBUFFERED"] = "1"

    print(f"  DEEPEVAL_RESULTS_FOLDER = {HIST}")
    print(f"  Working dir             = {DASH}")
    print(f"  Command                 = python run.py")
    print("\n" + "-" * 70)
    print("  Open in browser: http://localhost:5000")
    print("  Hard-refresh   : Ctrl + F5")
    print("  Stop dashboard : Ctrl + C in this terminal")
    print("-" * 70 + "\n")

    try:
        subprocess.run([sys.executable, str(RUN_PY)],
                       cwd=str(DASH), env=env, check=False)
    except KeyboardInterrupt:
        print("\n[OK] Stopped by user.")
    return 0


def main() -> int:
    print("=" * 70)
    print("Dashboard fix-and-start")
    print("=" * 70)
    install_missing_packages()
    kill_port(5000)
    return start_dashboard()


if __name__ == "__main__":
    sys.exit(main())