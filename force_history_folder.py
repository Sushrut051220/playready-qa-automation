"""
force_history_folder.py
=======================
The /api/settings POST returned 200 but the value didn't persist.
This script finds WHERE the dashboard actually stores settings (file or SQLite),
edits it directly, then prompts you to restart the dashboard.

Run:
    python force_history_folder.py
"""

from __future__ import annotations
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASH = ROOT / "Deepeval_Foundry_dashboard-main"
CORRECT_HISTORY = DASH / "eval_history"
WRONG_HISTORY = Path(r"C:\Users\v-snistane\OneDrive - Microsoft\deepeval-main\dashboard-main-local\eval_history")


def banner(s: str) -> None:
    print("\n" + "=" * 70)
    print(s)
    print("=" * 70)


# ---------- 1. find persistence ----------
def find_settings_files() -> list[Path]:
    """Look anywhere reasonable the dashboard might store settings."""
    candidates: list[Path] = []
    search_roots = [
        DASH,
        DASH / "eval_history",
        DASH / "backend",
        DASH / "data",
        Path.home() / ".deepeval",
        Path.home() / ".config" / "deepeval",
        Path(os.getenv("APPDATA", "")) / "deepeval" if os.getenv("APPDATA") else None,
        Path(os.getenv("LOCALAPPDATA", "")) / "deepeval" if os.getenv("LOCALAPPDATA") else None,
    ]
    needles = ("settings", "config", "preferences", "dashboard")
    for root in search_roots:
        if not root or not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() in {".json", ".db", ".sqlite", ".sqlite3", ".yaml", ".yml", ".toml"}:
                low = p.name.lower()
                if any(n in low for n in needles):
                    candidates.append(p)
    # de-dup
    seen, out = set(), []
    for p in candidates:
        s = str(p)
        if s not in seen:
            seen.add(s)
            out.append(p)
    return out


def find_files_referencing_wrong_path() -> list[Path]:
    """Find any JSON/SQLite that contains the wrong OneDrive path."""
    hits: list[Path] = []
    needle = "dashboard-main-local"
    for root in (DASH, Path.home() / ".deepeval",
                 Path(os.getenv("APPDATA", "")) / "deepeval" if os.getenv("APPDATA") else None,
                 Path(os.getenv("LOCALAPPDATA", "")) / "deepeval" if os.getenv("LOCALAPPDATA") else None):
        if not root or not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in {".json", ".db", ".sqlite", ".sqlite3"}:
                continue
            try:
                if p.suffix.lower() == ".json":
                    txt = p.read_text(encoding="utf-8", errors="ignore")
                    if needle in txt:
                        hits.append(p)
                else:
                    # SQLite: open and scan tables
                    try:
                        con = sqlite3.connect(p)
                        cur = con.cursor()
                        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = [r[0] for r in cur.fetchall()]
                        for t in tables:
                            try:
                                cur.execute(f"SELECT * FROM {t}")
                                rows = cur.fetchall()
                                if any(needle in str(r) for r in rows):
                                    hits.append(p)
                                    break
                            except Exception:
                                pass
                        con.close()
                    except Exception:
                        pass
            except Exception:
                pass
    # de-dup
    seen, out = set(), []
    for p in hits:
        s = str(p)
        if s not in seen:
            seen.add(s)
            out.append(p)
    return out


# ---------- 2. patch JSON ----------
def patch_json(path: Path) -> bool:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"    [SKIP] not valid JSON ({e})")
        return False

    changed = False
    new_path_str = str(CORRECT_HISTORY)

    def walk(node):
        nonlocal changed
        if isinstance(node, dict):
            for k, v in list(node.items()):
                if isinstance(v, str) and "dashboard-main-local" in v:
                    node[k] = new_path_str
                    changed = True
                elif isinstance(v, str) and k.lower() in {"historyfolder", "history_folder",
                                                          "results_folder", "resultsfolder",
                                                          "path", "folder"}:
                    if v != new_path_str:
                        node[k] = new_path_str
                        changed = True
                else:
                    walk(v)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                if isinstance(v, str) and "dashboard-main-local" in v:
                    node[i] = new_path_str
                    changed = True
                else:
                    walk(v)

    walk(obj)
    if changed:
        bk = path.with_suffix(path.suffix + f".bak_{datetime.now():%Y%m%d_%H%M%S}")
        shutil.copy2(path, bk)
        path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
        print(f"    [OK] patched (backup: {bk.name})")
        return True
    print("    [SKIP] no wrong path found in this JSON")
    return False


# ---------- 3. patch SQLite ----------
def patch_sqlite(path: Path) -> bool:
    new_path_str = str(CORRECT_HISTORY)
    changed = False
    try:
        bk = path.with_suffix(path.suffix + f".bak_{datetime.now():%Y%m%d_%H%M%S}")
        shutil.copy2(path, bk)
        con = sqlite3.connect(path)
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            try:
                cur.execute(f"PRAGMA table_info({t})")
                cols = [r[1] for r in cur.fetchall()]
                if not cols:
                    continue
                # build a generic UPDATE: scan every text column for the wrong substring
                for col in cols:
                    try:
                        cur.execute(
                            f"UPDATE {t} SET {col} = REPLACE({col}, ?, ?) "
                            f"WHERE {col} LIKE ?",
                            ("dashboard-main-local", "Deepeval_Foundry_dashboard-main",
                             "%dashboard-main-local%"),
                        )
                        if cur.rowcount > 0:
                            print(f"    [OK] {t}.{col}: {cur.rowcount} row(s) updated")
                            changed = True
                    except Exception:
                        pass
                # Also overwrite exact path-style fields
                for col in cols:
                    if col.lower() in {"historyfolder", "history_folder",
                                       "resultsfolder", "results_folder",
                                       "path", "folder", "value"}:
                        try:
                            cur.execute(
                                f"UPDATE {t} SET {col} = ? "
                                f"WHERE {col} LIKE ?",
                                (new_path_str, "%dashboard-main-local%"),
                            )
                            if cur.rowcount > 0:
                                print(f"    [OK] {t}.{col}: {cur.rowcount} row(s) fully replaced")
                                changed = True
                        except Exception:
                            pass
            except Exception:
                pass
        con.commit()
        con.close()
        if not changed:
            bk.unlink(missing_ok=True)
            print("    [SKIP] nothing matched")
        else:
            print(f"    backup: {bk.name}")
        return changed
    except Exception as e:
        print(f"    [FAIL] {e}")
        return False


def main() -> int:
    banner("force_history_folder")

    if not CORRECT_HISTORY.exists():
        print(f"[FAIL] Correct history folder missing: {CORRECT_HISTORY}")
        return 2

    runs = sorted(CORRECT_HISTORY.glob("test_run_*.json"))
    print(f"[OK] Correct folder ({CORRECT_HISTORY}) has {len(runs)} runs.")
    print(f"     Wrong folder is: {WRONG_HISTORY}")

    banner("[1/3] Searching for settings storage")
    candidates = find_settings_files()
    print(f"Found {len(candidates)} candidate settings files:")
    for c in candidates:
        print(f"  - {c}")

    banner("[2/3] Searching for files that REFERENCE the wrong path")
    refs = find_files_referencing_wrong_path()
    if not refs:
        print("No files currently reference 'dashboard-main-local'.")
        print("That means the value lives ONLY in the running process memory,")
        print("and our API POST didn't actually persist.")
    else:
        print(f"Found {len(refs)} files holding the wrong path:")
        for r in refs:
            print(f"  - {r}")

    banner("[3/3] Patching")
    if not refs and not candidates:
        print("[INFO] Nothing to patch. Falling through to last-resort options.")
    else:
        # Patch files that reference the wrong path
        for f in refs:
            print(f"\n  Patching: {f}")
            if f.suffix.lower() == ".json":
                patch_json(f)
            else:
                patch_sqlite(f)
        # Also try ANY settings file that doesn't reference wrong path but
        # has a history-folder-like key set to something else
        for f in candidates:
            if f in refs:
                continue
            if f.suffix.lower() == ".json":
                print(f"\n  Inspecting: {f}")
                patch_json(f)

    banner("Final instructions")
    print("1) Stop the dashboard (Ctrl+C in its terminal).")
    print("2) Restart it:")
    print("     python fix_and_start_dashboard.py")
    print("3) Log in, go to Settings page. Confirm History Folder is:")
    print(f"     {CORRECT_HISTORY}")
    print("4) If the path still shows the OneDrive value, set it MANUALLY")
    print("   via the Settings page and click Save.")
    print()
    print("OPTIONAL LAST RESORT — copy runs into the path the dashboard")
    print("is currently using (no patch needed, no restart needed):")
    print()
    print(f"   $src = '{CORRECT_HISTORY}'")
    print(f"   $dst = '{WRONG_HISTORY}'")
    print("   New-Item -ItemType Directory -Path $dst -Force | Out-Null")
    print("   Copy-Item -Path (Join-Path $src 'test_run_*.json') -Destination $dst -Force")
    print()
    print("   Then in the dashboard, click the refresh icon — all 7 runs appear.")
    return 0


if __name__ == "__main__":
    sys.exit(main())