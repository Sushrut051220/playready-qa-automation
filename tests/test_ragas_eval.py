# tests/test_ragas_eval.py  (FOUNDY-DATASET ONLY)

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAGAS_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "ragas"
ARCHIVED_REPORTS_DIR = PROJECT_ROOT / "artifacts" / "reports"
LATEST_REPORT_XLSX = PROJECT_ROOT / "reports" / "Latest_Report.xlsx"
DATASET_PATH = PROJECT_ROOT / "data" / "ragas_eval_dataset.json"


@pytest.mark.ragas
def test_run_ragas_eval() -> None:
    pytest.importorskip("ragas", reason="RAGAS is not installed in the active environment.")

    from ragas_layer.ragas_runner import run_ragas_evaluation

    if not DATASET_PATH.exists():
        pytest.fail(
            "Foundry dataset missing. Run scripts/query_foundry_agent.py first to generate data/ragas_eval_dataset.json"
        )

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8-sig"))

    results = run_ragas_evaluation(
        dataset,
        metrics_config={
            "answer_relevancy_threshold": float(os.getenv("RAGAS_ANSWER_RELEVANCY_THRESHOLD", "0.65")),
            "faithfulness_threshold": float(os.getenv("RAGAS_FAITHFULNESS_THRESHOLD", "0.70")),
        },
        output_dir=RAGAS_OUTPUT_DIR,
    )

    assert (RAGAS_OUTPUT_DIR / "ragas_results.json").exists(), "ragas_results.json was not created."
    assert LATEST_REPORT_XLSX.exists(), "reports/Latest_Report.xlsx was not created."

    archived_run_dirs = [p for p in ARCHIVED_REPORTS_DIR.iterdir() if p.is_dir()]
    assert archived_run_dirs, "No timestamped run folder found under artifacts/reports/."

    latest_run_dir = max(archived_run_dirs, key=lambda p: p.stat().st_mtime)
    assert (latest_run_dir / "ragas" / "ragas_results.json").exists(), "Timestamped ragas_results.json missing."

    executed = set(results.get("executed_metrics", []))
    if not executed:
        pytest.fail(f"No RAGAS metrics executed. Skipped: {results.get('skipped_metrics', [])}")