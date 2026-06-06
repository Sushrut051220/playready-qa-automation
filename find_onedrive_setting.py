"""
find_onedrive_setting.py
========================
The dashboard is using the OneDrive path even though it lives nowhere on disk.
That means it's set at startup by ONE of:
  A) an environment variable we missed (likely DEEPEVAL_RESULTS_FOLDER coming
     from your system env, OneDrive sync, .env file, or PowerShell profile)
  B) hardcoded in a config.py / __init__.py the dashboard loads
  C) loaded from a file inside the OneDrive folder itself

This finds it.

Run:
    python find_onedrive_setting.py
"""
from __future__ import annotations
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASH = ROOT / "Deepeval_Foundry_dashboard-main"
NEEDLES = ("dashboard-main-local", "OneDrive - Microsoft\\deepeval-main",
           "DEEPEVAL_RESULTS_FOLDER")


def main() -> int:
    print("=" * 70)
    print("Looking for the source of the OneDrive path")
    print("=" * 70)

    # A) live environment
    print("\n[A] Environment variables that could set the path:")
    for k, v in sorted(os.environ.items()):
        if "DEEPEVAL" in k.upper() or "HISTORY" in k.upper() or "RESULTS" in k.upper():
            print(f"     {k} = {v}")
    for scope in ("User", "Machine"):
        try:
            out = subprocess.check_output(
                ["powershell", "-Command",
                 f"[Environment]::GetEnvironmentVariables('{scope}') | "
                 f"Format-List | Out-String"],
                text=True, errors="ignore",
            )
            for line in out.splitlines():
                if any(n.lower() in line.lower() for n in
                       ("DEEPEVAL_", "DASHBOARD", "EVAL_HISTORY")):
                    print(f"     [{scope}] {line.strip()}")
        except Exception:
            pass

    # B) hardcoded in dashboard source
    print("\n[B] Hardcoded references in dashboard source:")
    hits = 0
    for p in DASH.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(txt.splitlines(), 1):
            if any(n in line for n in NEEDLES):
                print(f"     {p.relative_to(DASH)}:{i}  {line.strip()[:160]}")
                hits += 1
    if hits == 0:
        print("     (no hardcoded references found)")

    # C) PowerShell profile
    print("\n[C] PowerShell profile env exports:")
    try:
        prof = subprocess.check_output(
            ["powershell", "-Command", "$PROFILE | Get-Item -ErrorAction SilentlyContinue | Get-Content -Raw"],
            text=True, errors="ignore",
        )
        for line in prof.splitlines():
            if any(n.lower() in line.lower() for n in ("deepeval", "eval_history", "dashboard")):
                print(f"     {line.strip()}")
    except Exception:
        pass

    # D) .env files
    print("\n[D] .env files containing the path:")
    for env_file in ROOT.rglob(".env*"):
        if ".venv" in env_file.parts:
            continue
        try:
            txt = env_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(txt.splitlines(), 1):
            if any(n in line for n in NEEDLES):
                print(f"     {env_file}:{i}  {line.strip()[:160]}")

    print("\n" + "=" * 70)
    print("Most likely source: section [A] User-scope DEEPEVAL_RESULTS_FOLDER")
    print("=" * 70)
    print("If you find it there, clear it with:")
    print('  [Environment]::SetEnvironmentVariable("DEEPEVAL_RESULTS_FOLDER", $null, "User")')
    print("Then restart PowerShell and the dashboard.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())