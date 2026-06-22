#!/usr/bin/env python3
"""
fix_deepeval.py
===============
Adds evaluation_params=[INPUT, ACTUAL_OUTPUT] to every GEval(...) call
in deepeval_layer/deepeval_evaluator.py if missing.

Safe to re-run (idempotent).
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "deepeval_layer" / "deepeval_evaluator.py"

EVAL_PARAMS_LINE = "        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],"


def main() -> int:
    if not TARGET.exists():
        print(f"[ERROR] {TARGET} not found")
        return 1

    text = TARGET.read_text(encoding="utf-8")
    original = text

    # 1) Ensure LLMTestCaseParams is imported
    if "LLMTestCaseParams" not in text:
        text = re.sub(
            r"from\s+deepeval\.test_case\s+import\s+LLMTestCase(?![A-Za-z])",
            "from deepeval.test_case import LLMTestCase, LLMTestCaseParams",
            text,
            count=1,
        )
        print("[+] Added LLMTestCaseParams import")

    # 2) Find every GEval(...) call and patch
    # We split the file into lines and walk forward, tracking parentheses depth
    lines = text.splitlines(keepends=True)
    out_lines: list[str] = []
    i = 0
    patched = 0

    while i < len(lines):
        line = lines[i]

        # Look for the start of a GEval( call
        if "GEval(" in line and "evaluation_params" not in line:
            # Find the matching close paren - track paren depth
            block_start = i
            depth = 0
            found_close = False
            block_text = ""

            for j in range(i, len(lines)):
                block_text += lines[j]
                for ch in lines[j]:
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                        if depth == 0:
                            block_end = j
                            found_close = True
                            break
                if found_close:
                    break

            if found_close and "evaluation_params" not in block_text:
                # Emit lines before the closing paren
                for k in range(block_start, block_end):
                    out_lines.append(lines[k])

                # Find indent of the closing-paren line; insert eval_params just above it
                close_line = lines[block_end]
                close_indent = re.match(r"(\s*)", close_line).group(1)
                inject = f"{close_indent}    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],\n"

                # Ensure the line before the close has a trailing comma
                # (Walk back through out_lines to find the last non-empty/non-comment content)
                idx_back = len(out_lines) - 1
                while idx_back >= 0 and out_lines[idx_back].strip() in ("", ):
                    idx_back -= 1
                if idx_back >= 0:
                    prev = out_lines[idx_back].rstrip("\n")
                    if not prev.rstrip().endswith(","):
                        out_lines[idx_back] = prev + ",\n"

                out_lines.append(inject)
                out_lines.append(close_line)
                patched += 1
                i = block_end + 1
                continue
            else:
                # Couldn't find close or already patched - emit as-is
                out_lines.append(line)
                i += 1
                continue

        out_lines.append(line)
        i += 1

    if patched == 0 and text == original:
        print("[OK] No changes needed (already patched or no GEval calls found)")
        return 0

    new_text = "".join(out_lines)

    # Backup
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bk_dir = ROOT / "backups" / f"deepeval_evalparams_{ts}"
    bk_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TARGET, bk_dir / TARGET.name)
    print(f"[BACKUP] {bk_dir / TARGET.name}")

    TARGET.write_text(new_text, encoding="utf-8")
    print(f"[OK] Patched {patched} GEval block(s)")

    # Syntax check via compile()
    try:
        compile(new_text, str(TARGET), "exec")
        print("[OK] Syntax valid")
    except SyntaxError as e:
        print(f"[ERROR] Syntax error after patch: {e}")
        print(f"  Restore from {bk_dir / TARGET.name}")
        return 1

    # Show what was added
    print("\nVerification (lines containing evaluation_params):")
    for n, ln in enumerate(new_text.splitlines(), start=1):
        if "evaluation_params" in ln:
            print(f"  Line {n}: {ln.strip()}")

    print("\nNow run:")
    print('  python -c "from deepeval_layer.deepeval_evaluator import run_deepeval_evaluation; run_deepeval_evaluation(bot_type=\'public\', limit=5)"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())