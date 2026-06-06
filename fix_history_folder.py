"""
fix_history_folder.py
=====================
Your dashboard backend is configured to read from:
   C:\\Users\\v-snistane\\OneDrive - Microsoft\\deepeval-main\\dashboard-main-local\\eval_history
But your runs are written to:
   C:\\Users\\v-snistane\\playready-qa-automation\\Deepeval_Foundry_dashboard-main\\eval_history

This script logs in and POSTs the correct path to /api/settings.

Run:
    python fix_history_folder.py
"""

from __future__ import annotations
import getpass
import json
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

BASE = "http://localhost:5000"
ROOT = Path(__file__).resolve().parent
CORRECT_HISTORY = ROOT / "Deepeval_Foundry_dashboard-main" / "eval_history"


def make_opener():
    cj = CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)), cj


def http(opener, method: str, path: str, payload: dict | None = None,
         timeout: float = 8.0) -> tuple[int, str]:
    url = BASE + path
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        return e.code, body
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def short(s: str, n: int = 300) -> str:
    return s if len(s) <= n else s[:n] + f"...[{len(s)} chars]"


def main() -> int:
    print("=" * 70)
    print("Fix dashboard historyFolder")
    print("=" * 70)

    if not CORRECT_HISTORY.exists():
        print(f"[FAIL] Target folder does not exist:\n  {CORRECT_HISTORY}")
        return 2

    runs = sorted(CORRECT_HISTORY.glob("test_run_*.json"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    print(f"\n[OK] Target folder has {len(runs)} test_run_*.json files:")
    for r in runs[:5]:
        print(f"     - {r.name}  ({r.stat().st_size:,} bytes)")

    user = input("\nUsername ").strip() or "admin"
    pw = getpass.getpass("Password: ").strip()
    if not pw:
        print("[FAIL] Empty password.")
        return 3

    opener, _ = make_opener()

    # 1) login
    code, body = http(opener, "POST", "/api/auth/login",
                      {"username": user, "password": pw})
    print(f"\n[1] Login                       HTTP {code}")
    if code != 200:
        print(f"    {short(body)}")
        return 4
    print(f"    [OK] Logged in as {user}")

    # 2) show current settings
    code, body = http(opener, "GET", "/api/settings")
    print(f"\n[2] Current /api/settings       HTTP {code}")
    try:
        cur = json.loads(body)
        print(f"    historyFolder : {cur.get('historyFolder')}")
        print(f"    runCount      : {cur.get('runCount')}")
    except Exception:
        print(f"    {short(body)}")

    # 3) update historyFolder
    new_path = str(CORRECT_HISTORY)
    print(f"\n[3] Setting historyFolder to:\n    {new_path}")

    # Try a few common payload shapes — the openapi spec showed
    # body.historyFolder, so this is the canonical one
    payloads = [
        {"historyFolder": new_path},
        {"history_folder": new_path},
        {"path": new_path},
    ]
    success = False
    for payload in payloads:
        for method in ("POST", "PUT", "PATCH"):
            code, body = http(opener, method, "/api/settings", payload)
            tag = "  <-- ACCEPTED" if code in (200, 201, 204) else ""
            print(f"    {method:<5} /api/settings  payload={list(payload.keys())} -> HTTP {code}{tag}")
            if code in (200, 201, 204):
                success = True
                break
        if success:
            break

    if not success:
        print("\n[FAIL] None of the settings update calls succeeded.")
        print("       Use the dashboard UI instead:")
        print("         1. Open http://localhost:5000")
        print("         2. Click Settings (gear icon)")
        print(f"         3. Set History Folder to:\n            {new_path}")
        print("         4. Save")
        return 5

    # 4) verify
    code, body = http(opener, "GET", "/api/settings")
    print(f"\n[4] Verified /api/settings      HTTP {code}")
    try:
        cur = json.loads(body)
        print(f"    historyFolder : {cur.get('historyFolder')}")
        print(f"    runCount      : {cur.get('runCount')}")
    except Exception:
        print(f"    {short(body)}")

    # 5) verify /api/runs now sees them
    code, body = http(opener, "GET", "/api/runs?limit=100")
    print(f"\n[5] GET /api/runs               HTTP {code}")
    try:
        data = json.loads(body)
        runs_list = data.get("data") if isinstance(data, dict) else data
        if isinstance(runs_list, list):
            print(f"    [OK] {len(runs_list)} runs now visible to the API")
            for r in runs_list[:8]:
                if isinstance(r, dict):
                    print(f"      - {r.get('filename')}  passed={r.get('testPassed')} failed={r.get('testFailed')}")
        else:
            print(f"    {short(body)}")
    except Exception:
        print(f"    {short(body)}")

    print("\n" + "=" * 70)
    print("Now open http://localhost:5000  (hard refresh Ctrl+Shift+R)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())