"""
deep_trace_history_folder.py
============================
We found the bug: backend/config.py reads DEEPEVAL_RESULTS_FOLDER only ONCE at
import time. The dashboard is somehow getting the OneDrive path at startup.

This script:
  1. Reads backend/config.py and confirms the freeze-at-import behavior.
  2. Reads backend/routers/settings.py to see what the POST actually does.
  3. Looks for OTHER places that might compute the path differently
     (run_loader, file_watcher, online_eval_worker).
  4. Tests what the dashboard process is using RIGHT NOW (via /api/runs/<file>).

Run:
    python deep_trace_history_folder.py
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASH = ROOT / "Deepeval_Foundry_dashboard-main"
BACKEND = DASH / "backend"

NEEDLES = re.compile(
    r"HISTORY_FOLDER|DEEPEVAL_RESULTS_FOLDER|historyFolder|history_folder|eval_history",
    re.I,
)

CRITICAL_FILES = [
    BACKEND / "config.py",
    BACKEND / "routers" / "settings.py",
    BACKEND / "services" / "run_loader.py",
    BACKEND / "services" / "file_watcher.py",
    BACKEND / "services" / "online_eval_worker.py",
    BACKEND / "routers" / "runs.py",
    BACKEND / "main.py",
]


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def dump_file_lines(path: Path) -> None:
    if not path.exists():
        print(f"  [SKIP] {path.relative_to(DASH)} not found")
        return
    print(f"\n  --- {path.relative_to(DASH)} ---")
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"  [ERR] {e}")
        return
    for i, line in enumerate(text.splitlines(), 1):
        if NEEDLES.search(line):
            print(f"  {i:>4}: {line}")


def main() -> int:
    print_section("[1] backend/config.py — where HISTORY_FOLDER is born")
    dump_file_lines(BACKEND / "config.py")

    print_section("[2] settings.py — the POST handler")
    dump_file_lines(BACKEND / "routers" / "settings.py")

    print_section("[3] run_loader.py — the actual reader of test_run_*.json")
    dump_file_lines(BACKEND / "services" / "run_loader.py")

    print_section("[4] file_watcher.py — what folder the watcher monitors")
    dump_file_lines(BACKEND / "services" / "file_watcher.py")

    print_section("[5] online_eval_worker.py")
    dump_file_lines(BACKEND / "services" / "online_eval_worker.py")

    print_section("[6] runs.py — the API the UI calls")
    dump_file_lines(BACKEND / "routers" / "runs.py")

    print_section("[7] main.py — startup wiring")
    dump_file_lines(BACKEND / "main.py")

    print_section("Diagnosis hints")
    print("Look at section [1]: does HISTORY_FOLDER come ONLY from")
    print("os.getenv('DEEPEVAL_RESULTS_FOLDER', './eval_history')?")
    print("If yes, the OneDrive path must be coming from somewhere ELSE at startup.")
    print()
    print("Look at section [3] and [4]: do they reference HISTORY_FOLDER directly,")
    print("or do they re-read os.getenv() each time? That tells us whether changing")
    print("the env var at runtime would even help.")
    return 0


if __name__ == "__main__":
    sys.exit(main())