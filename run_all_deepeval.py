"""
run_all_deepeval.py (auto-discovery version)
=============================================
Discovers ALL `run_deepeval_*_evaluation` functions in deepeval_layer/
and runs each one, then merges results into ONE Excel report.

Adding a new track? Just create a function named `run_deepeval_<NAME>_evaluation`
in deepeval_layer/deepeval_evaluator.py. This script picks it up automatically.

Usage:
    python run_all_deepeval.py --bot-type public --limit 5
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Bootstrap path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv()


# ─── Discovery: find all `run_deepeval_*_evaluation` functions ──────────────
def discover_eval_functions(module):
    """Find all functions matching `run_deepeval_*_evaluation` pattern.
    Excludes deterministic fallbacks (`*_deterministic`) so we only run LLM variants.
    """
    candidates = []
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if not name.startswith("run_deepeval_"):
            continue
        if not name.endswith("_evaluation"):
            continue
        if name.endswith("_deterministic"):
            continue  # skip deterministic fallbacks
        candidates.append((name, obj))
    # Stable order: alphabetical
    return sorted(candidates, key=lambda x: x[0])


# ─── JSON merging ───────────────────────────────────────────────────────────
def merge_all_jsons(json_paths, eval_history_dir, bot_type):
    """Merge N dashboard JSONs into one combined JSON."""
    combined = {
        "testCases": [],
        "conversationalTestCases": [],
        "metricsScores": [],
        "testPassed": 0,
        "testFailed": 0,
        "runDuration": 0.0,
        "evaluationCost": 0.0,
        "hyperparameters": {},
        "identifier": "deepeval-combined",
    }

    for path in json_paths:
        if not path or not path.exists():
            continue
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [WARN] Could not read {path.name}: {e}")
            continue
        combined["testCases"].extend(d.get("testCases", []) or [])
        combined["conversationalTestCases"].extend(d.get("conversationalTestCases", []) or [])
        combined["metricsScores"].extend(d.get("metricsScores", []) or [])
        combined["testPassed"] += d.get("testPassed", 0) or 0
        combined["testFailed"] += d.get("testFailed", 0) or 0
        combined["runDuration"] += d.get("runDuration") or 0.0
        combined["evaluationCost"] += d.get("evaluationCost") or 0.0
        # Merge hyperparameters (later tracks override earlier ones)
        if d.get("hyperparameters"):
            combined["hyperparameters"].update(d["hyperparameters"])

    combined["hyperparameters"]["tracks"] = f"{len(json_paths)} combined"
    combined["hyperparameters"]["bot_type"] = bot_type

    timestamp = int(time.time())
    out = eval_history_dir / f"test_run_deepeval_combined_{timestamp}.json"
    out.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def get_track_label(func_name):
    """Extract a friendly name from `run_deepeval_<NAME>_evaluation`."""
    # run_deepeval_evaluation -> single-turn
    # run_deepeval_conversational_evaluation -> conversational
    # run_deepeval_safety_evaluation -> safety
    stem = func_name.replace("run_deepeval_", "").replace("_evaluation", "")
    return stem if stem else "single-turn"


# ─── Main ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Auto-discover and run ALL DeepEval evaluations; produce ONE combined Excel."
    )
    parser.add_argument("--bot-type", choices=["public", "customer", "private"], default="public")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--model", default=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-mini"))
    parser.add_argument("--environment", default="production")
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument(
        "--skip",
        nargs="*",
        default=[],
        help="Names of tracks to skip (e.g. --skip conversational)",
    )
    args = parser.parse_args()

    os.environ["BOT_TYPE"] = args.bot_type

    # Discover available tracks
    from deepeval_layer import deepeval_evaluator
    tracks = discover_eval_functions(deepeval_evaluator)
    if not tracks:
        print("[ERROR] No `run_deepeval_*_evaluation` functions found")
        return 1

    print("=" * 70)
    print(f"  DeepEval Combined Evaluation - {len(tracks)} track(s) discovered")
    print(f"  bot_type={args.bot_type}  limit={args.limit}  model={args.model}")
    print("=" * 70)
    for name, _ in tracks:
        label = get_track_label(name)
        marker = "[SKIP]" if label in args.skip else "[RUN] "
        print(f"  {marker} {label:30s} ({name})")

    eval_dir = Path(
        os.getenv("DEEPEVAL_RESULTS_FOLDER")
        or r"C:\Users\v-snistane\tools\deepeval-dashboard\eval_history"
    )
    eval_dir.mkdir(parents=True, exist_ok=True)

    # Track each new JSON produced
    json_paths = []
    existing = set(p.name for p in eval_dir.glob("test_run_deepeval_*.json"))

    for func_name, func in tracks:
        label = get_track_label(func_name)
        if label in args.skip:
            print(f"\n[SKIP] {label}")
            continue

        print("\n" + "─" * 70)
        print(f"  Running: {label} ({func_name})")
        print("─" * 70)

        try:
            # Build kwargs based on function signature
            sig = inspect.signature(func)
            kwargs = {}
            for param_name in ("limit", "bot_type", "model", "environment", "version"):
                if param_name in sig.parameters:
                    kwargs[param_name] = getattr(args, param_name)
            func(**kwargs)
        except Exception as e:
            print(f"[ERROR] {label} failed: {e}")
            continue

        # Find the new JSON produced by this track
        after = sorted(eval_dir.glob("test_run_deepeval_*.json"), key=lambda p: p.stat().st_mtime)
        new_json = next((p for p in reversed(after) if p.name not in existing), None)
        if new_json:
            print(f"  [{label}] JSON -> {new_json.name}")
            json_paths.append(new_json)
            existing.add(new_json.name)
        else:
            print(f"  [WARN] No new JSON produced by {label}")

    if not json_paths:
        print("[ERROR] No JSONs were produced - cannot generate combined report")
        return 1

    # Merge all into combined JSON
    print("\n" + "─" * 70)
    print(f"  Merging {len(json_paths)} JSON(s) into unified report")
    print("─" * 70)
    combined_json = merge_all_jsons(json_paths, eval_dir, args.bot_type)
    print(f"  Combined JSON -> {combined_json.name}")

    # Generate combined Excel
    from deepeval_layer.deepeval_excel_report import generate_deepeval_report_from_json
    excel_dir = _ROOT / "reports" / "deepeval"
    excel_dir.mkdir(parents=True, exist_ok=True)
    excel_path = generate_deepeval_report_from_json(combined_json, output_dir=excel_dir)
    print(f"  Combined Excel -> {excel_path}")

    print("\n" + "=" * 70)
    print("  Combined evaluation complete")
    for jp in json_paths:
        print(f"  - {jp.name}")
    print(f"  Combined JSON: {combined_json.name}")
    print(f"  Combined Excel: {excel_path.name}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
