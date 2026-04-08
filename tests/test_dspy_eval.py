from __future__ import annotations

import os
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "ui_runs"
DSPY_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "dspy"


@pytest.mark.dspy
def test_run_dspy_eval() -> None:
    pytest.importorskip("dspy", reason="DSPy is not installed in the active environment.")
    from dspy_layer.ui_to_dspy import convert_ui_artifacts_to_dspy_examples, run_dspy_evaluation

    if not UI_ARTIFACT_DIR.exists() or not any(UI_ARTIFACT_DIR.glob("*.json")):
        pytest.skip("Run the UI capture suite first so artifacts are available.")

    examples = convert_ui_artifacts_to_dspy_examples(UI_ARTIFACT_DIR)
    if not examples:
        pytest.skip("No UI artifacts were found in artifacts/ui_runs.")

    results = run_dspy_evaluation(examples, output_path=DSPY_OUTPUT_DIR)
    summary = results["summary"]
    min_score = float(os.getenv("DSPY_MIN_SCORE", "0.70"))

    assert (DSPY_OUTPUT_DIR / "dspy_results.json").exists(), "DSPy results JSON was not created."
    assert summary["average_score"] >= min_score, (
        f"DSPy average score {summary['average_score']} is below threshold {min_score}."
    )
    assert summary.get("strict_grounding_failures", 0) == 0, (
        "One or more strict-grounding cases matched an unexpected PDF. "
        "Inspect artifacts/dspy/dspy_results.json for details."
    )
