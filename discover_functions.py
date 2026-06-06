"""
discover_functions.py
=====================
Lists all function and method definitions across the 4 pipeline files
so we can pinpoint exactly where to add tracing decorators.
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TARGETS = [
    ROOT / "scripts" / "run_ragas_bridge.py",
    ROOT / "scripts" / "query_new_agent.py",
    ROOT / "ragas_layer" / "ragas_runner.py",
    ROOT / "ragas_layer" / "dashboard_bridge.py",
    ROOT / "foundry_layer" / "foundry_evaluator.py",
]


def summarize(path: Path) -> None:
    print("\n" + "=" * 78)
    print(f"FILE: {path.relative_to(ROOT)}")
    print("=" * 78)
    if not path.exists():
        print("  [MISSING]")
        return

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  [PARSE ERROR] {e}")
        return

    # Top-level defs
    print("\n-- Top-level functions --")
    found_top = False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found_top = True
            args = ", ".join(a.arg for a in node.args.args)
            print(f"  L{node.lineno:>4}: def {node.name}({args})")
    if not found_top:
        print("  (none)")

    # Classes + methods
    print("\n-- Classes / methods --")
    found_cls = False
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            found_cls = True
            print(f"  L{node.lineno:>4}: class {node.name}")
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = ", ".join(a.arg for a in sub.args.args)
                    print(f"        L{sub.lineno:>4}: def {sub.name}({args})")
    if not found_cls:
        print("  (none)")

    # Look for things that look like Foundry calls
    print("\n-- Calls that look like Foundry/agent/HTTP --")
    src = path.read_text(encoding="utf-8")
    needles = [
        "create_thread", "create_run", "create_and_run",
        "get_messages", "list_messages",
        "agent_id", "thread_id", "run_id",
        "agents.runs", "agents.threads", ".messages.",
        "AzureOpenAI(", "AIProjectClient", "DefaultAzureCredential",
        "openai.chat", "client.chat",
        "citations", "retrieved_chunks", "retrieved_contexts",
    ]
    hits = []
    for lineno, line in enumerate(src.splitlines(), 1):
        for n in needles:
            if n in line:
                hits.append((lineno, n, line.strip()[:140]))
                break
    if not hits:
        print("  (no relevant call patterns detected)")
    else:
        for lineno, needle, txt in hits[:25]:
            print(f"  L{lineno:>4}  [{needle:<22}]  {txt}")
        if len(hits) > 25:
            print(f"  ... {len(hits) - 25} more")


def main() -> int:
    for p in TARGETS:
        summarize(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
