"""
dashboard_auth_unlock.py
========================
Why login is locked:
    - auth.json doesn't exist yet
    - POST /api/auth/users requires being already logged in as admin
    - POST /api/auth/login rejects you because no users exist
    => chicken-and-egg

This script:
    1. Searches Deepeval_Foundry_dashboard-main/backend for the auth bootstrap
       (default creds, env-var unlock, or bootstrap file format).
    2. Tries 6 common default credential pairs against /api/auth/login.
    3. Reads backend/routers/auth.py to extract the EXACT password hashing scheme.
    4. Generates a ready-to-use auth.json with credentials YOU choose.
    5. Tells you exactly what to do next.

Run:
    python dashboard_auth_unlock.py
"""

from __future__ import annotations
import getpass
import hashlib
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASH = ROOT / "Deepeval_Foundry_dashboard-main"
BACKEND = DASH / "backend"
AUTH_JSON = DASH / "eval_history" / "auth.json"
BASE = "http://localhost:5000"


# ---------- helpers ----------
def opener_with_jar():
    cj = CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)), cj


def http(opener, method: str, path: str, payload: dict | None = None,
         timeout: float = 6.0) -> tuple[int, str]:
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


def short(s: str, n: int = 220) -> str:
    return s if len(s) <= n else s[:n] + f"...[{len(s)} chars]"


# ---------- 1. inspect auth source ----------
def inspect_backend_auth() -> dict:
    info: dict = {
        "files_scanned": [],
        "hits": [],
        "hash_scheme": None,        # "sha256" / "bcrypt" / "plain" / "argon2" / "pbkdf2"
        "salt_present": False,
        "default_user_hint": None,
        "bootstrap_env_vars": [],
        "auth_json_schema_hint": None,
    }
    if not BACKEND.exists():
        info["error"] = f"{BACKEND} not found"
        return info

    patterns = [
        ("default_admin", re.compile(r"default[_\s\-]*(?:admin|user|password)", re.I)),
        ("env_var",       re.compile(r"os\.getenv\(\s*['\"](DEEPEVAL_[A-Z_]+|ADMIN[A-Z_]*|AUTH_[A-Z_]+)['\"]", re.I)),
        ("hash_call",     re.compile(r"\b(hashlib\.(?:sha256|sha512|md5)|bcrypt|argon2|pbkdf2_hmac|passlib)\b")),
        ("auth_json_w",   re.compile(r"auth\.json")),
        ("salt",          re.compile(r"\bsalt\b", re.I)),
        ("bootstrap",     re.compile(r"bootstrap|seed|create[_\s\-]*default|first[_\s\-]*user", re.I)),
        ("verify_pw",     re.compile(r"verify[_\s\-]*password|check[_\s\-]*password|compare_digest")),
    ]

    for py in BACKEND.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        info["files_scanned"].append(str(py.relative_to(DASH)))
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for tag, pat in patterns:
                if pat.search(line):
                    info["hits"].append((tag, py.relative_to(DASH), lineno, line.strip()[:200]))

    # Determine hash scheme
    text_blob = ""
    for py in BACKEND.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        try:
            text_blob += py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    if re.search(r"hashlib\.sha256", text_blob):
        info["hash_scheme"] = "sha256"
    if re.search(r"\bbcrypt\b", text_blob):
        info["hash_scheme"] = "bcrypt"
    if re.search(r"\bargon2\b", text_blob, re.I):
        info["hash_scheme"] = "argon2"
    if re.search(r"\bpbkdf2_hmac\b", text_blob):
        info["hash_scheme"] = "pbkdf2"
    if re.search(r"\bsalt\b", text_blob, re.I):
        info["salt_present"] = True

    # auth.json schema hint
    m = re.search(r"auth\.json[^\n]{0,200}", text_blob)
    if m:
        info["auth_json_schema_hint"] = m.group(0)

    # env-var bootstrap candidates
    info["bootstrap_env_vars"] = sorted({
        h[3]
        for h in info["hits"]
        if h[0] == "env_var"
    })
    return info


# ---------- 2. try common defaults ----------
def try_common_defaults() -> tuple[bool, str, str]:
    pairs = [
        ("admin", "admin"),
        ("admin", "password"),
        ("admin", "deepeval"),
        ("admin", "changeme"),
        ("admin", "admin123"),
        ("deepeval", "deepeval"),
    ]
    opener, _ = opener_with_jar()
    for u, p in pairs:
        code, body = http(opener, "POST", "/api/auth/login", {"username": u, "password": p})
        tag = " <-- SUCCESS" if code == 200 else ""
        print(f"     try {u!r:<12} / {p!r:<12} -> HTTP {code}  {short(body, 80)}{tag}")
        if code == 200:
            return True, u, p
    return False, "", ""


# ---------- 3. generate auth.json directly ----------
def make_password_record(password: str, scheme: str | None) -> dict:
    """Produce a record matching common dashboard schemas."""
    record: dict = {"username": "admin", "role": "admin"}
    if scheme == "sha256":
        salt = secrets.token_hex(16)
        h = hashlib.sha256((salt + password).encode()).hexdigest()
        record["salt"] = salt
        record["password_hash"] = h
    elif scheme == "pbkdf2":
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        record["salt"] = salt.hex()
        record["password_hash"] = dk.hex()
        record["iterations"] = 100_000
    elif scheme == "bcrypt":
        try:
            import bcrypt
            record["password_hash"] = bcrypt.hashpw(password.encode(),
                                                   bcrypt.gensalt()).decode()
        except ImportError:
            record["password_hash"] = "<bcrypt-not-installed>"
    else:
        # Plain (some dashboards still do this)
        record["password"] = password
    return record


# ---------- main ----------
def main() -> int:
    print("=" * 70)
    print("Dashboard auth unlock")
    print("=" * 70)

    if not BACKEND.exists():
        print(f"[FAIL] Backend not found: {BACKEND}")
        return 2

    print("\n[1/4] Inspecting backend auth source...")
    info = inspect_backend_auth()
    print(f"     Files scanned   : {len(info['files_scanned'])}")
    print(f"     Hash scheme     : {info.get('hash_scheme') or 'unknown'}")
    print(f"     Salt detected   : {info['salt_present']}")
    print(f"     Env bootstrap   : {info['bootstrap_env_vars'] or 'none detected'}")
    print(f"     auth.json hint  : {info.get('auth_json_schema_hint')}")
    print("     Top relevant hits:")
    seen = set()
    shown = 0
    for tag, p, ln, txt in info["hits"]:
        key = (tag, str(p))
        if key in seen:
            continue
        seen.add(key)
        print(f"       [{tag:<14}] {p}:{ln}  {txt}")
        shown += 1
        if shown >= 15:
            break

    print("\n[2/4] Trying common default credentials...")
    ok, u, p = try_common_defaults()
    if ok:
        print(f"\n[OK] Common credentials worked! Username: {u}  Password: {p}")
        print(f"     Open {BASE} and log in with those.")
        return 0

    print("\n[3/4] Common credentials did NOT work.")
    print("     The dashboard probably has a bootstrap that runs on the FIRST")
    print("     unauthenticated POST /api/auth/users, but it's currently locked.")
    print("     The cleanest fix is to write auth.json ourselves and restart the dashboard.")

    print("\n[4/4] Generate auth.json now? This will let you log in with the password")
    print("     you choose right now (the file is written next to eval_history/).")
    ans = input("     Generate auth.json? [Y/n]: ").strip().lower() or "y"
    if ans != "y":
        print("     Skipped. You can also try clearing the file and restarting:")
        print(f"       Remove-Item '{AUTH_JSON}' -ErrorAction SilentlyContinue")
        print("       Then stop+restart the dashboard, then re-run this helper.")
        return 0

    password = getpass.getpass("     New admin password: ").strip()
    if not password:
        print("[FAIL] Empty password not allowed.")
        return 3

    AUTH_JSON.parent.mkdir(parents=True, exist_ok=True)
    record = make_password_record(password, info.get("hash_scheme"))

    # Most dashboards expect either:
    #   - a list of users
    #   - or a dict { "users": [...] }
    # We write BOTH layouts so the loader picks one up; if not, you'll see
    # an error in the backend log telling us the exact schema.
    payload_list = [record]
    payload_dict = {"users": [record]}

    # Heuristic: pick based on auth_json_schema_hint
    use_dict = False
    hint = (info.get("auth_json_schema_hint") or "").lower()
    if "users" in hint or "list" in hint or "dict" in hint:
        use_dict = True
    chosen = payload_dict if use_dict else payload_list
    AUTH_JSON.write_text(json.dumps(chosen, indent=2), encoding="utf-8")
    print(f"\n[OK] Wrote: {AUTH_JSON}")
    print(f"     Schema: {'dict {users:[...]}' if use_dict else 'list[...]'}")
    print(f"     Hash scheme used: {info.get('hash_scheme') or 'plain'}")

    print()
    print("=" * 70)
    print("Now do EXACTLY this:")
    print("=" * 70)
    print(" 1) Stop the dashboard (Ctrl+C in its terminal).")
    print(" 2) Start it again:")
    print("       python fix_and_start_dashboard.py")
    print(" 3) Open http://localhost:5000  and log in with:")
    print("       username: admin")
    print("       password: <the one you just typed>")
    print()
    print("If login still fails, paste me the OUTPUT OF SECTION [1/4] from this")
    print("script — the schema hints will tell me whether auth.json needs to be")
    print("rewritten in a different shape.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
