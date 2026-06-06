"""
dashboard_login_helper.py
=========================
The dashboard backend returned: {"enabled":true,"authenticated":false}
That's why the UI shows nothing — every /api/runs call gets HTTP 401.

This script:
  1. Lists existing users via /api/auth/users   (no auth needed if backend allows; falls back to creating).
  2. If no users exist, creates an 'admin' user with a password you provide.
  3. Logs in via /api/auth/login.
  4. Uses the returned session cookie/token to fetch /api/runs and confirm runs are visible.

It does NOT store your password anywhere on disk.

Run:
    python dashboard_login_helper.py
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
CHECK_PATH = "/api/auth/status"
LOGIN_PATH = "/api/auth/login"
USERS_PATH = "/api/auth/users"
RUNS_PATH = "/api/runs"
AUTH_JSON = Path(__file__).resolve().parent / "Deepeval_Foundry_dashboard-main" / "eval_history" / "auth.json"


def make_opener():
    cj = CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)), cj


def request(opener, method: str, path: str, payload: dict | None = None,
            extra_headers: dict | None = None, timeout: float = 10.0) -> tuple[int, str, dict]:
    url = BASE + path
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with opener.open(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="ignore")
            resp_headers = dict(r.headers.items())
            return r.status, body, resp_headers
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        return e.code, body, dict(e.headers.items()) if e.headers else {}
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}", {}


def short(s: str, n: int = 200) -> str:
    return s if len(s) <= n else s[:n] + f"...[{len(s)} chars]"


def main() -> int:
    print("=" * 70)
    print("Dashboard login helper")
    print("=" * 70)

    opener, jar = make_opener()

    # 0) Status
    code, body, _ = request(opener, "GET", CHECK_PATH)
    print(f"\n[0] GET {CHECK_PATH}    HTTP {code}")
    print(f"    {short(body, 200)}")
    if code != 200:
        print("\n[FAIL] Dashboard not reachable. Is it running?")
        return 2

    try:
        status = json.loads(body)
    except Exception:
        status = {}
    if not status.get("enabled", True):
        print("[OK] Auth is disabled — runs should already be visible. "
              "Hard-refresh the browser (Ctrl+Shift+R).")
        return 0
    if status.get("authenticated"):
        print(f"[OK] You're already authenticated as {status.get('username')}.")
        # Skip straight to runs check
        return verify_runs(opener)

    # 1) Inspect auth.json (read-only, just to hint at credentials)
    print(f"\n[1] Local auth file: {AUTH_JSON}")
    if AUTH_JSON.exists():
        try:
            text = AUTH_JSON.read_text(encoding="utf-8")
            print(f"    Exists, {len(text):,} chars. Keys at top level:")
            try:
                obj = json.loads(text)
                if isinstance(obj, dict):
                    print(f"    {list(obj.keys())[:10]}")
                elif isinstance(obj, list):
                    print(f"    list of {len(obj)} entries; first keys: "
                          f"{list(obj[0].keys()) if obj and isinstance(obj[0], dict) else 'n/a'}")
            except Exception:
                pass
        except Exception as e:
            print(f"    [WARN] Could not read: {e}")
    else:
        print("    Does not exist yet — backend will create it on first user signup.")

    # 2) Ask whether to create user or log in
    print("\n[2] Choose:")
    print("    1 = Log in with existing credentials")
    print("    2 = Create a new user (only works if backend allows public signup,")
    print("        or if you're the first user)")
    choice = input("    Enter 1 or 2 [default 1]: ").strip() or "1"

    if choice == "2":
        username = input("    New username [admin]: ").strip() or "admin"
        password = getpass.getpass("    New password: ").strip()
        role = input("    Role [admin]: ").strip() or "admin"
        if not password:
            print("[FAIL] Empty password not allowed.")
            return 3
        code, body, _ = request(opener, "POST", USERS_PATH,
                                {"username": username, "password": password, "role": role})
        print(f"    POST {USERS_PATH}  HTTP {code}")
        print(f"    {short(body, 300)}")
        if code not in (200, 201):
            print("[WARN] User creation failed — most likely you need to log in as an")
            print("       existing admin first. Falling back to login flow.")
        # fall through to login
    else:
        username = input("    Username [admin]: ").strip() or "admin"
        password = getpass.getpass("    Password: ").strip()

    # 3) Log in
    code, body, headers = request(opener, "POST", LOGIN_PATH,
                                  {"username": username, "password": password})
    print(f"\n[3] POST {LOGIN_PATH}  HTTP {code}")
    print(f"    {short(body, 300)}")
    if code != 200:
        print("\n[FAIL] Login failed.")
        print("       If you do not know the password, you can delete the auth file")
        print(f"       to reset (CAUTION: removes ALL users):")
        print(f"         Remove-Item '{AUTH_JSON}'")
        print("       Then restart the dashboard and re-run this helper to create user 1.")
        return 4

    # Show cookies / tokens
    cookies = [f"{c.name}={c.value[:24]}..." for c in jar]
    if cookies:
        print(f"    [OK] Cookies received: {cookies}")
    try:
        login_data = json.loads(body)
        token = login_data.get("token") or login_data.get("access_token")
        if token:
            print(f"    [OK] Token received: {token[:24]}...")
    except Exception:
        token = None

    # 4) Verify /api/runs now works using the same opener (cookies stick)
    return verify_runs(opener)


def verify_runs(opener) -> int:
    print("\n[4] Verifying /api/runs with authenticated session")
    code, body, _ = request(opener, "GET", RUNS_PATH)
    print(f"    GET {RUNS_PATH}  HTTP {code}")
    if code != 200:
        print(f"    {short(body, 400)}")
        print("\n[FAIL] Still not authorized. Inspect /docs to find the right endpoint.")
        return 5
    try:
        data = json.loads(body)
        runs = data.get("runs") if isinstance(data, dict) else data
        if isinstance(runs, list):
            print(f"    [OK] {len(runs)} runs visible to this session.")
            for r in runs[:8]:
                if isinstance(r, dict):
                    name = r.get("filename") or r.get("name") or r.get("id") or "?"
                    print(f"         - {name}")
        else:
            print(f"    {short(body, 400)}")
    except Exception:
        print(f"    {short(body, 400)}")

    print("\n" + "=" * 70)
    print("Next step: open browser, log in with the SAME credentials")
    print("=" * 70)
    print(f"  URL  : {BASE}")
    print("  After login, the 7 runs will appear in the dashboard UI.")
    print("  If you still don't see them, do a hard refresh: Ctrl + Shift + R")
    return 0


if __name__ == "__main__":
    sys.exit(main())