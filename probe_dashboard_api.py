"""
probe_dashboard_api.py
======================
The dashboard backend logs 'Loaded runs: 7' but the browser shows nothing.
This script talks to the FastAPI backend directly to find out why.

Run:
    python probe_dashboard_api.py
"""

from __future__ import annotations
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

BASE = "http://localhost:5000"


def get(path: str, timeout: float = 5.0) -> tuple[int, str]:
    url = BASE + path
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
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


def short(s: str, n: int = 400) -> str:
    return s if len(s) <= n else s[:n] + f"... [truncated, total {len(s)} chars]"


def main() -> int:
    print("=" * 70)
    print(f"Probing dashboard at {BASE}")
    print("=" * 70)

    # 1) Sanity: backend reachable?
    code, body = get("/docs")
    print(f"\n[1] GET /docs                 -> HTTP {code}")
    if code == 0:
        print(f"    {body}")
        print("\n[FAIL] Dashboard backend is NOT reachable on port 5000.")
        print("       Make sure fix_and_start_dashboard.py is still running.")
        return 2

    # 2) OpenAPI: discover real endpoint paths
    code, body = get("/openapi.json")
    print(f"[2] GET /openapi.json         -> HTTP {code}  ({len(body):,} bytes)")
    endpoints: list[str] = []
    if code == 200:
        try:
            spec = json.loads(body)
            for path, methods in spec.get("paths", {}).items():
                for method in methods:
                    endpoints.append(f"{method.upper():6} {path}")
        except Exception as e:
            print(f"    [WARN] could not parse openapi: {e}")
    print(f"    Endpoints found: {len(endpoints)}")
    for ep in endpoints[:30]:
        print(f"      {ep}")
    if len(endpoints) > 30:
        print(f"      ... ({len(endpoints) - 30} more)")

    # 3) Probe candidate run-list endpoints
    candidates = [
        "/api/runs", "/runs", "/api/v1/runs",
        "/api/history", "/history",
        "/api/test_runs", "/test_runs",
        "/api/eval_history", "/eval_history",
    ]
    print(f"\n[3] Probing run-list endpoints:")
    found_runs_endpoint = None
    for path in candidates:
        code, body = get(path)
        tag = ""
        if code == 200 and ("test_run_" in body or "testCases" in body
                            or '"runs"' in body or body.startswith("[")):
            tag = "  <-- looks like a run list"
            found_runs_endpoint = found_runs_endpoint or path
        print(f"    {path:<22} HTTP {code:<5} {short(body, 100)}{tag}")

    # 4) Show one run via the discovered endpoint
    if found_runs_endpoint:
        print(f"\n[4] Fetching {found_runs_endpoint} for run summary...")
        code, body = get(found_runs_endpoint)
        try:
            data = json.loads(body)
            if isinstance(data, dict) and "runs" in data:
                runs = data["runs"]
            elif isinstance(data, list):
                runs = data
            else:
                runs = []
            print(f"    Runs returned by API: {len(runs)}")
            for r in runs[:5]:
                if isinstance(r, dict):
                    keys = list(r.keys())[:6]
                    name = r.get("filename") or r.get("name") or r.get("id") or "?"
                    print(f"      - {name}    keys={keys}")
                else:
                    print(f"      - {r}")
        except Exception as e:
            print(f"    [WARN] Could not parse run list: {e}")
            print(f"    Raw: {short(body, 300)}")

    # 5) Auth check
    print(f"\n[5] Auth check:")
    for path in ("/api/auth/status", "/auth/status", "/api/me", "/me"):
        code, body = get(path)
        if code != 404:
            print(f"    {path:<22} HTTP {code} {short(body, 150)}")

    # 6) Frontend index
    print(f"\n[6] Frontend index:")
    code, body = get("/")
    print(f"    GET /                       HTTP {code}  ({len(body):,} bytes)")
    if code == 200:
        lower = body.lower()
        is_html = "<html" in lower
        has_react = "react" in lower or "_next" in lower or "vite" in lower
        has_login = "login" in lower or "sign in" in lower or "password" in lower
        print(f"    HTML page : {is_html}")
        print(f"    SPA framework hints : {has_react}")
        print(f"    Mentions login/sign-in : {has_login}")

    print("\n" + "=" * 70)
    print("Interpretation guide")
    print("=" * 70)
    print("- If [3] found a runs endpoint returning >=1 runs but the UI is empty,")
    print("  the BACKEND is fine. Fix is browser-side:")
    print("    * Hard-refresh with Ctrl+Shift+R")
    print("    * Open DevTools (F12) -> Network tab -> reload -> look for red requests")
    print("    * Try an incognito/private window")
    print("- If [5] hints at login required, you must create or log in with an account.")
    print("  Check Deepeval_Foundry_dashboard-main/eval_history/auth.json")
    print("- If [3] returns 0 runs even though backend logged 'Loaded runs: 7', the")
    print("  endpoint filters by date/status/auth. Send THIS script's output to chat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())