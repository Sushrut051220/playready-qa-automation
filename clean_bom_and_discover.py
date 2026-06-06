"""
clean_bom_and_discover.py
=========================
Strips the UTF-8 BOM from query_new_agent.py and prints its functions
so we know which ones to decorate.
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "scripts" / "query_new_agent.py"

if not TARGET.exists():
    print(f"[FAIL] {TARGET} not found")
    sys.exit(2)

raw = TARGET.read_bytes()
if raw.startswith(b"\xef\xbb\xbf"):
    bk = TARGET.with_suffix(".py.bak_bom")
    bk.write_bytes(raw)
    TARGET.write_bytes(raw[3:])
    print(f"[OK] Stripped BOM. Backup: {bk.name}")
else:
    print("[OK] No BOM present.")

print("\n" + "=" * 78)
print(f"FILE: {TARGET.relative_to(ROOT)}")
print("=" * 78)
try:
    tree = ast.parse(TARGET.read_text(encoding="utf-8"))
except Exception as e:
    print(f"  [PARSE ERROR] {e}")
    sys.exit(3)

print("\n-- Top-level functions --")
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = ", ".join(a.arg for a in node.args.args)
        print(f"  L{node.lineno:>4}: def {node.name}({args})")

print("\n-- Classes / methods --")
for node in tree.body:
    if isinstance(node, ast.ClassDef):
        print(f"  L{node.lineno:>4}: class {node.name}")
        for sub in node.body:
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = ", ".join(a.arg for a in sub.args.args)
                print(f"        L{sub.lineno:>4}: def {sub.name}({args})")

print("\n-- Suspicious lines --")
needles = ["create_thread","create_run","get_messages","list_messages",
           "agents.runs","agents.threads",".messages.","AIProjectClient",
           "DefaultAzureCredential","citations","retrieved_chunks","retrieved_contexts",
           "AzureOpenAI("]
src = TARGET.read_text(encoding="utf-8")
for lineno, line in enumerate(src.splitlines(), 1):
    for n in needles:
        if n in line:
            print(f"  L{lineno:>4}  [{n:<22}]  {line.strip()[:140]}")
            break
