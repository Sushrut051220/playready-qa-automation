"""
check_project_save.py
=====================
Confirms whether the dashboard saved your 'playready-foundry' display config
and explains why no card shows up yet.

Run:
    python check_project_save.py
"""
from __future__ import annotations
import getpass, json, sys, urllib.error, urllib.request
from http.cookiejar import CookieJar

BASE = "http://localhost:5000"
USER = "admin"


def make_opener():
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(CookieJar()))


def http(opener, method, path, payload=None):
    data = json.dumps(payload).encode() if payload else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with opener.open(req, timeout=8) as r:
            return r.status, r.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode("utf-8", errors="ignore") if e.fp else "")


def main():
    pw = getpass.getpass(f"Password for {USER}: ")
    op = make_opener()
    code, _ = http(op, "POST", "/api/auth/login", {"username": USER, "password": pw})
    if code != 200:
        print("[FAIL] login failed"); return 2
    print("[OK] logged in")

    for path in ("/api/projects", "/api/projects/ids", "/api/projects/configure"):
        code, body = http(op, "GET", path)
        print(f"\nGET {path}  HTTP {code}")
        try:
            obj = json.loads(body)
            print(json.dumps(obj, indent=2)[:1500])
        except Exception:
            print(body[:400])

    return 0


if __name__ == "__main__":
    sys.exit(main())
