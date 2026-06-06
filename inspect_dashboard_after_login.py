"""
inspect_dashboard_after_login.py
================================
Logs in to the dashboard (using credentials you provide), then probes the
exact API endpoints the React frontend calls, so we can see what the UI sees.

Run:
    python inspect_dashboard_after_login.py
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
HIST = ROOT / "Deepeval_Foundry_dashboard-main" / "eval_history"


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


def short(s: str, n: int = 600) -> str:
    return s if len(s) <= n else s[:n] + f"...[{len(s)} chars total]"


def parse_or_raw(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None


def main() -> int:
    print("=" * 70)
    print("Inspect dashboard AFTER login (mimics what the React UI does)")
    print("=" * 70)

    user = input("Username [admin]: ").strip() or "admin"
    pw = getpass.getpass("Password: ").strip()
    if not pw:
        print("[FAIL] Empty password.")
        return 2

    opener, _ = make_opener()

    # 1) login
    code, body = http(opener, "POST", "/api/auth/login",
                      {"username": user, "password": pw})
    print(f"\n[1] POST /api/auth/login        HTTP {code}")
    print(f"    {short(body, 240)}")
    if code != 200:
        print("[FAIL] Login failed. Use the helper from previous step.")
        return 3

    # 2) confirm session
    code, body = http(opener, "GET", "/api/auth/status")
    print(f"\n[2] GET  /api/auth/status       HTTP {code}")
    print(f"    {short(body, 240)}")

    # 3) probe the real endpoints the UI uses
    print("\n[3] Probing /api endpoints that drive the UI:")
    endpoints = [
        "/api/runs",
        "/api/runs?limit=100",
        "/api/runs?page=1&size=100",
        "/api/runs/latest",
        "/api/projects",
        "/api/projects/ids",
        "/api/benchmarks",
        "/api/sla/status",
        "/api/eval-metrics",
        "/api/playground/eval-metrics",
    ]
    results: dict[str, tuple[int, object]] = {}
    for ep in endpoints:
        code, body = http(opener, "GET", ep)
        parsed = parse_or_raw(body)
        results[ep] = (code, parsed if parsed is not None else body)
        tag = ""
        if isinstance(parsed, list):
            tag = f"  list[{len(parsed)}]"
        elif isinstance(parsed, dict):
            for k in ("runs", "items", "data", "results"):
                v = parsed.get(k)
                if isinstance(v, list):
                    tag = f"  {k}=list[{len(v)}]"
                    break
            if not tag and parsed:
                tag = f"  dict keys={list(parsed.keys())[:6]}"
        print(f"   {ep:<42} HTTP {code} {tag}")

    # 4) dig into /api/runs — the critical one
    print("\n[4] Inspect /api/runs payload shape:")
    code, body = http(opener, "GET", "/api/runs")
    parsed = parse_or_raw(body)
    if parsed is None:
        print(f"    Not JSON. First 400 chars:\n    {short(body, 400)}")
    else:
        if isinstance(parsed, dict):
            print(f"    Top-level keys: {list(parsed.keys())}")
            runs = None
            for k in ("runs", "items", "data", "results"):
                if isinstance(parsed.get(k), list):
                    runs = parsed[k]
                    print(f"    Used key: {k}  -> {len(runs)} runs")
                    break
        elif isinstance(parsed, list):
            runs = parsed
            print(f"    Top-level is list of {len(runs)} runs")
        else:
            runs = None
            print(f"    Unexpected JSON shape: {type(parsed).__name__}")

        if runs:
            print("\n    First run keys + values (first 12 fields):")
            r = runs[0]
            if isinstance(r, dict):
                items = list(r.items())[:12]
                for k, v in items:
                    rep = str(v)
                    if len(rep) > 80:
                        rep = rep[:80] + "..."
                    print(f"      {k:<22} = {rep}")
            print(f"\n    Filenames in API:")
            for r in runs[:10]:
                if isinstance(r, dict):
                    name = r.get("filename") or r.get("name") or r.get("file") or r.get("id") or r.get("path")
                    print(f"      - {name}")

    # 5) compare to what's on disk
    print("\n[5] Compare to JSON files on disk:")
    if HIST.exists():
        on_disk = sorted(HIST.glob("test_run_*.json"),
                         key=lambda p: p.stat().st_mtime, reverse=True)
        print(f"    On-disk files: {len(on_disk)}")
        for f in on_disk[:10]:
            print(f"      - {f.name}  ({f.stat().st_size:,} bytes)")
    else:
        print(f"    [WARN] {HIST} does not exist")

    # 6) settings + project assignment
    print("\n[6] Settings + project assignment:")
    for ep in ("/api/settings", "/api/settings/active", "/api/projects/ids"):
        code, body = http(opener, "GET", ep)
        parsed = parse_or_raw(body)
        print(f"    GET {ep:<26} HTTP {code} {short(json.dumps(parsed) if parsed is not None else body, 240)}")

    print("\n" + "=" * 70)
    print("READ THIS")
    print("=" * 70)
    print(" - If /api/runs returns 7 runs but the UI is blank, the React frontend")
    print("   is filtering by something (project, date range, status). Paste this")
    print("   whole output back to chat — I'll send a targeted fix.")
    print(" - If /api/runs returns 0 runs while the disk has 7, the backend filter")
    print("   is the problem (cache / project scoping). Same: paste the output.")
    print(" - If /api/runs returns 0 but /api/projects has zero projects, then")
    print("   the dashboard requires a project to be created first.")
    return 0


if __name__ == "__main__":
    sys.exit(main())