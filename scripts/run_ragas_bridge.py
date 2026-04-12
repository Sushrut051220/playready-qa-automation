"""Run RAGAS evaluation directly on the bridge dataset (data/ragas_eval_dataset.json)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from datasets import Dataset
from ragas_layer.ragas_runner import run_ragas_evaluation

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_DATASET = PROJECT_ROOT / "data" / "ragas_eval_dataset.json"
RAGAS_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "ragas"

os.environ.setdefault("RAGAS_METRICS_PROFILE", "full")

rows = json.loads(BRIDGE_DATASET.read_text(encoding="utf-8"))
ds = Dataset.from_list(rows)
print(f"Dataset: {ds.num_rows} rows | columns: {ds.column_names}")

results = run_ragas_evaluation(ds, output_dir=str(RAGAS_OUTPUT_DIR))

print("\n=== EXECUTED METRICS ===")
for m in results.get("executed_metrics", []):
    score = results.get("summary", {}).get(m)
    print(f"  + {m}: {score}")

print("\n=== SKIPPED METRICS ===")
for s in results.get("skipped_metrics", []):
    print(f"  - {s['metric']}: {s['reason']}")

print(f"\nResults saved to: {RAGAS_OUTPUT_DIR / 'ragas_results.json'}")
