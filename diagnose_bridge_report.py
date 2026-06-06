"""
diagnose_bridge_report.py
=========================
Locates _generate_bridge_excel_report() in audit/reporting.py, prints the
function source, and reports whether `rows` is referenced without being
defined inside the function.

Run:
    python diagnose_bridge_report.py
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "audit" / "reporting.py"
FUNC_NAME = "_generate_bridge_excel_report"


def extract_function(source: str, func_name: str) -> tuple[int, int, str] | None:
    """Return (start_line, end_line, source) for the first def matching func_name."""
    lines = source.splitlines()
    start = None
    indent = None
    for i, line in enumerate(lines):
        if re.match(rf"^\s*def\s+{re.escape(func_name)}\s*\(", line):
            start = i
            indent = len(line) - len(line.lstrip())
            break
    if start is None:
        return None

    # Find end: next line at same or lower indent that is non-blank def/class/code
    end = len(lines)
    for j in range(start + 1, len(lines)):
        ln = lines[j]
        if ln.strip() == "":
            continue
        cur_indent = len(ln) - len(ln.lstrip())
        if cur_indent <= indent and (ln.lstrip().startswith(("def ", "class ", "@"))
                                     or not ln.startswith(" ")):
            end = j
            break

    return (start + 1, end, "\n".join(lines[start:end]))


def main() -> int:
    if not TARGET.exists():
        print(f"[FAIL] Not found: {TARGET}")
        return 2

    src = TARGET.read_text(encoding="utf-8")
    result = extract_function(src, FUNC_NAME)
    if not result:
        print(f"[FAIL] Could not find def {FUNC_NAME}(...) in {TARGET.name}")
        return 3

    start_line, end_line, body = result
    print(f"[OK] Found {FUNC_NAME} at lines {start_line}-{end_line}")
    print("=" * 70)
    print(body)
    print("=" * 70)

    # Heuristic check for the bug
    refs_rows = re.findall(r"\brows\b", body)
    defs_rows = re.findall(r"^\s*rows\s*=", body, flags=re.MULTILINE)
    print(f"\n'rows' references in function : {len(refs_rows)}")
    print(f"'rows = ...' definitions       : {len(defs_rows)}")

    if refs_rows and not defs_rows:
        print("\n[DIAGNOSIS] Confirmed: `rows` is referenced but never assigned inside the function.")
        print("            Send this output to chat to receive the exact patch.")
    elif refs_rows and defs_rows:
        print("\n[DIAGNOSIS] `rows` IS assigned somewhere — bug may be a scope/order issue.")
        print("            Send this output to chat for review.")
    else:
        print("\n[DIAGNOSIS] No `rows` references — the NameError may come from elsewhere.")

    return 0


if __name__ == "__main__":
    sys.exit(main())