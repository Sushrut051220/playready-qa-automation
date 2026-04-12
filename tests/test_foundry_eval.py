from __future__ import annotations

import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "ragas_eval_dataset.json"
FOUNDRY_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "foundry"


@pytest.mark.foundry_eval
def test_run_foundry_evaluation() -> None:
    from foundry_layer.foundry_evaluator import run_all_foundry_evaluations

    if not DATASET_PATH.exists():
        pytest.fail(
            "Foundry dataset missing. Run scripts/query_foundry_agent.py first to generate "
            "data/ragas_eval_dataset.json"
        )

    results = run_all_foundry_evaluations(
        dataset_path=DATASET_PATH,
        output_dir=FOUNDRY_OUTPUT_DIR,
    )

    # NLP should always run (no LLM needed)
    assert results["nlp"]["status"] == "completed", "NLP evaluation did not complete."
    assert (FOUNDRY_OUTPUT_DIR / "foundry_nlp.json").exists(), "foundry_nlp.json was not created."

    # Quality may be skipped if Azure OpenAI not configured
    assert (FOUNDRY_OUTPUT_DIR / "foundry_quality.json").exists(), "foundry_quality.json was not created."

    # Safety may be skipped if Azure AI Project not configured
    assert (FOUNDRY_OUTPUT_DIR / "foundry_safety.json").exists(), "foundry_safety.json was not created."

    # Summary
    assert (FOUNDRY_OUTPUT_DIR / "foundry_summary.json").exists(), "foundry_summary.json was not created."