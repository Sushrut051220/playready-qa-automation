"""
probe_trace_api.py
==================
Probes the dashboard backend to discover the trace schema it expects.
"""
import getpass, json, sys, urllib.request, urllib.error
from http.cookiejar import CookieJar

BASE = "http://localhost:5000"


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
    except Exception as e:
        return 0, str(e)


def main():
    pw = getpass.getpass("Password for admin: ")
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    code, _ = http(op, "POST", "/api/auth/login", {"username": "admin", "password": pw})
    if code != 200:
        print("[FAIL] login failed"); return 2

    code, body = http(op, "GET", "/openapi.json")
    if code != 200:
        print("[FAIL] openapi unreachable"); return 3
    spec = json.loads(body)
    trace_paths = [p for p in spec.get("paths", {}) if "trace" in p.lower() or "span" in p.lower()]
    print(f"Trace-related endpoints: {len(trace_paths)}")
    for p in trace_paths:
        methods = list(spec["paths"][p].keys())
        print(f"  {','.join(m.upper() for m in methods):<10} {p}")

    for ep in ("/api/traces", "/api/spans"):
        code, body = http(op, "GET", ep)
        print(f"\nGET {ep}  HTTP {code}")
        print(f"  {body[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
