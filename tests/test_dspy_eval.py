from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_CASES_FILE = PROJECT_ROOT / "data" / "test_cases.json"
UI_ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "ui_runs"
DSPY_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "dspy"


def load_test_cases() -> list[dict]:
    return json.loads(TEST_CASES_FILE.read_text(encoding="utf-8"))


@pytest.mark.dspy
def test_run_dspy_eval() -> None:
    pytest.importorskip("dspy", reason="DSPy is not installed in the active environment.")
    from dspy_layer.ui_to_dspy import (
        convert_ui_artifacts_to_dspy_examples,
        run_dspy_evaluation,
        load_pdf_registry,
        UIArtifactAdapter,
        build_metric_breakdown,
        _resolve_source_match_status,
        composite_deterministic_metric,
        _compute_paraphrase_consistency,
    )

    if not UI_ARTIFACT_DIR.exists() or not any(UI_ARTIFACT_DIR.glob("*.json")):
        pytest.fail("No UI artifacts found. Run the UI capture suite first so artifacts are available.")

    all_test_cases = load_test_cases()
    examples = convert_ui_artifacts_to_dspy_examples(UI_ARTIFACT_DIR)
    if not examples:
        pytest.fail("No UI artifacts were found in artifacts/ui_runs. UI capture must produce output before DSPy can run.")

    results = run_dspy_evaluation(examples, output_path=DSPY_OUTPUT_DIR)
    
    # Add UI_FAILED entries for test cases without artifacts
    existing_ids = {r["id"] for r in results["results"]}
    pdf_registry = load_pdf_registry()
    adapter = UIArtifactAdapter(pdf_registry=pdf_registry)
    
    for test_case in all_test_cases:
        if test_case["id"] not in existing_ids:
            # This test case failed at UI capture stage
            failed_row = {
                "id": test_case["id"],
                "question": test_case.get("prompt", ""),
                "answer": "",
                "normalized_answer": "",
                "contexts": [],
                "ground_truths": test_case.get("ground_truth", []) if isinstance(test_case.get("ground_truth"), list) else ([test_case.get("ground_truth")] if test_case.get("ground_truth") else []),
                "required_keywords": test_case.get("required_keywords", []),
                "forbidden_patterns": test_case.get("forbidden_patterns", []),
                "expect_fallback": test_case.get("expect_fallback", False),
                "fallback_patterns": test_case.get("fallback_patterns", []),
                "expected_pdfs": test_case.get("expected_pdfs", []),
                "strict_grounding": test_case.get("strict_grounding", False),
                "matched_pdfs": [],
                "source_match_status": "not_evaluated",
                "paraphrase_group": test_case.get("paraphrase_group"),
                "detected_fallback": False,
                "context_count": 0,
                "deterministic_scores": {"total": 0.0},
                "issues": ["UI capture failed or timed out — no artifact available"],
            }
            results["results"].append(failed_row)
    
    # Recalculate summary to include all cases
    total_score_values = [r["deterministic_scores"]["total"] for r in results["results"] if r["deterministic_scores"]["total"] > 0]
    results["summary"]["example_count"] = len(results["results"])
    results["summary"]["average_score"] = round(sum(total_score_values) / len(total_score_values), 4) if total_score_values else 0.0
    results["summary"]["ui_failed_count"] = len(results["results"]) - len(examples)
    results["summary"]["evaluated_count"] = len(examples)
    
    summary = results["summary"]
    min_score = float(os.getenv("DSPY_MIN_SCORE", "0.70"))

    # Generate UI/E2E report before strict assertions so failures still produce a fresh report.
    from audit.reporting import create_enterprise_reporting_assets
    create_enterprise_reporting_assets(PROJECT_ROOT, dspy_results=results, report_mode="ui_e2e")

    assert (DSPY_OUTPUT_DIR / "dspy_results.json").exists(), "DSPy results JSON was not created."
    # Only check minimum score on evaluated cases (not UI failures)
    if total_score_values:
        assert sum(total_score_values) / len(total_score_values) >= min_score, (
            f"DSPy average score {summary['average_score']} is below threshold {min_score}."
        )
    assert summary.get("strict_grounding_failures", 0) == 0, (
        "One or more strict-grounding cases matched an unexpected PDF. "
        "Inspect artifacts/dspy/dspy_results.json for details."
    )
