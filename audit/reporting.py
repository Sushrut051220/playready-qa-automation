from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


RUN_FOLDER_FORMAT = "%Y-%m-%d_%H-%M-%S"
COPYABLE_SUFFIXES = {".json", ".csv", ".html", ".txt", ".png", ".zip"}
GREEN_FILL = PatternFill(fill_type="solid", fgColor="C6EFCE")
RED_FILL = PatternFill(fill_type="solid", fgColor="FFC7CE")
YELLOW_FILL = PatternFill(fill_type="solid", fgColor="FFEB9C")
BLUE_FILL = PatternFill(fill_type="solid", fgColor="DDEBF7")
HEADER_FILL = PatternFill(fill_type="solid", fgColor="D9EAF7")
HEADER_FONT = Font(bold=True)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _strip_nonce(text: str | None) -> str:
    return re.sub(r"\s*\[RUN:[^\]]+\]\s*", "", str(text or "")).strip()


def _copy_tree(src: Path, dest: Path) -> None:
    if not src.exists():
        return

    for path in src.rglob("*"):
        if path.is_dir() or path.suffix.lower() not in COPYABLE_SUFFIXES:
            continue
        target = dest / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _copy_file_if_exists(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def _load_ui_artifacts(ui_dir: Path) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    if not ui_dir.exists():
        return artifacts

    for artifact_file in sorted(ui_dir.glob("*.json")):
        payload = _load_json(artifact_file)
        if payload:
            test_id = str(payload.get("id") or payload.get("test_id") or artifact_file.stem)
            artifacts[test_id] = payload
    return artifacts


def _load_test_cases(project_root: Path) -> dict[str, dict[str, Any]]:
    cases_path = project_root / "data" / "test_cases.json"
    if not cases_path.exists():
        return {}
    try:
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {str(item.get("id")): item for item in cases if item.get("id")}


def _read_float(raw_value: Any, default: float) -> float:
    try:
        return float(raw_value)
    except Exception:
        return float(default)


def _build_metric_thresholds(ragas_results: dict[str, Any]) -> dict[str, float]:
    ragas_thresholds = ragas_results.get("thresholds", {}) if isinstance(ragas_results, dict) else {}
    return {
        "dspy_total_score": _read_float(os.getenv("DSPY_MIN_SCORE", "0.40"), 0.40),
        "dspy_keyword_score": _read_float(os.getenv("DSPY_KEYWORD_THRESHOLD", "1.0"), 1.0),
        "dspy_fallback_score": _read_float(os.getenv("DSPY_FALLBACK_THRESHOLD", "1.0"), 1.0),
        "dspy_format_score": _read_float(os.getenv("DSPY_FORMAT_THRESHOLD", "1.0"), 1.0),
        "dspy_pdf_grounding_score": _read_float(os.getenv("DSPY_PDF_GROUNDING_THRESHOLD", "1.0"), 1.0),
        "ragas_answer_relevancy": _read_float(
            ragas_thresholds.get("answer_relevancy", os.getenv("RAGAS_ANSWER_RELEVANCY_THRESHOLD", "0.65")),
            0.65,
        ),
        "ragas_answer_accuracy": _read_float(
            ragas_thresholds.get("answer_accuracy", os.getenv("RAGAS_ANSWER_ACCURACY_THRESHOLD", "0.70")),
            0.70,
        ),
        "ragas_faithfulness": _read_float(
            ragas_thresholds.get("faithfulness", os.getenv("RAGAS_FAITHFULNESS_THRESHOLD", "0.70")),
            0.70,
        ),
        "ragas_context_precision": _read_float(
            ragas_thresholds.get("context_precision", os.getenv("RAGAS_CONTEXT_PRECISION_THRESHOLD", "0.70")),
            0.70,
        ),
        "ragas_context_utilization": _read_float(
            ragas_thresholds.get("context_utilization", os.getenv("RAGAS_CONTEXT_UTILIZATION_THRESHOLD", "0.70")),
            0.70,
        ),
        "ragas_context_recall": _read_float(
            ragas_thresholds.get("context_recall", os.getenv("RAGAS_CONTEXT_RECALL_THRESHOLD", "0.70")),
            0.70,
        ),
        "ragas_context_relevance": _read_float(
            ragas_thresholds.get("context_relevance", os.getenv("RAGAS_CONTEXT_RELEVANCE_THRESHOLD", "0.70")),
            0.70,
        ),
        "ragas_response_groundedness": _read_float(
            ragas_thresholds.get("response_groundedness", os.getenv("RAGAS_RESPONSE_GROUNDEDNESS_THRESHOLD", "0.70")),
            0.70,
        ),
        "ragas_context_entity_recall": _read_float(
            ragas_thresholds.get("context_entity_recall", os.getenv("RAGAS_CONTEXT_ENTITY_RECALL_THRESHOLD", "0.70")),
            0.70,
        ),
        "ragas_noise_sensitivity_relevant": _read_float(
            ragas_thresholds.get("noise_sensitivity_relevant", os.getenv("RAGAS_NOISE_SENSITIVITY_RELEVANT_THRESHOLD", "0.30")),
            0.30,
        ),
        "ragas_noise_sensitivity_irrelevant": _read_float(
            ragas_thresholds.get("noise_sensitivity_irrelevant", os.getenv("RAGAS_NOISE_SENSITIVITY_IRRELEVANT_THRESHOLD", "0.30")),
            0.30,
        ),
    }


def _build_metric_operators() -> dict[str, str]:
    return {
        "dspy_total_score": ">=",
        "dspy_keyword_score": ">=",
        "dspy_fallback_score": ">=",
        "dspy_format_score": ">=",
        "dspy_pdf_grounding_score": ">=",
        "ragas_answer_relevancy": ">=",
        "ragas_answer_accuracy": ">=",
        "ragas_faithfulness": ">=",
        "ragas_context_precision": ">=",
        "ragas_context_utilization": ">=",
        "ragas_context_recall": ">=",
        "ragas_context_relevance": ">=",
        "ragas_response_groundedness": ">=",
        "ragas_context_entity_recall": ">=",
        "ragas_noise_sensitivity_relevant": "<=",
        "ragas_noise_sensitivity_irrelevant": "<=",
    }


def _classify_metric_result(value: Any, threshold: float, operator: str = ">=") -> str:
    if value in (None, ""):
        return "N/A"
    try:
        numeric_value = float(value)
        numeric_threshold = float(threshold)
        if operator == "<=":
            return "PASS" if numeric_value <= numeric_threshold else "FAIL"
        return "PASS" if numeric_value >= numeric_threshold else "FAIL"
    except Exception:
        return "N/A"


def _build_results_rows(
    project_root: Path,
    ui_artifacts: dict[str, dict[str, Any]],
    dspy_results: dict[str, Any],
    ragas_results: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, float]]:
    dspy_rows = dspy_results.get("results", []) if isinstance(dspy_results, dict) else []
    dspy_by_id = {str(row.get("id")): row for row in dspy_rows if row.get("id") is not None}
    ragas_rows = ragas_results.get("rows", []) if isinstance(ragas_results, dict) else []
    ragas_by_id = {str(row.get("id")): row for row in ragas_rows if row.get("id") is not None}
    ragas_by_question = {
        _strip_nonce(row.get("question") or row.get("user_input")): row
        for row in ragas_rows
        if _strip_nonce(row.get("question") or row.get("user_input"))
    }
    test_cases_by_id = _load_test_cases(project_root)
    metric_thresholds = _build_metric_thresholds(ragas_results)
    metric_operators = _build_metric_operators()
    metric_order = [
        "dspy_total_score",
        "dspy_keyword_score",
        "dspy_fallback_score",
        "dspy_format_score",
        "dspy_pdf_grounding_score",
        "ragas_answer_relevancy",
        "ragas_answer_accuracy",
        "ragas_faithfulness",
        "ragas_context_precision",
        "ragas_context_utilization",
        "ragas_context_recall",
        "ragas_context_relevance",
        "ragas_response_groundedness",
        "ragas_context_entity_recall",
        "ragas_noise_sensitivity_relevant",
        "ragas_noise_sensitivity_irrelevant",
    ]
    metric_counters = {metric: {"PASS": 0, "FAIL": 0, "N/A": 0} for metric in metric_order}

    results_rows: list[dict[str, Any]] = []
    failures_only_rows: list[dict[str, Any]] = []

    for test_id, payload in ui_artifacts.items():
        answer_text = str(payload.get("answer_text") or payload.get("answer") or "").strip()
        base_prompt = _strip_nonce(payload.get("base_prompt") or payload.get("prompt"))
        dspy_row = dspy_by_id.get(test_id, {})
        ragas_row = ragas_by_id.get(test_id) or ragas_by_question.get(base_prompt, {})
        test_case = test_cases_by_id.get(test_id, {})
        deterministic_scores = dspy_row.get("deterministic_scores") or {}

        expected_pdfs = dspy_row.get("expected_pdfs") or payload.get("expected_pdfs") or test_case.get("expected_pdfs") or []
        matched_pdfs = dspy_row.get("matched_pdfs") or payload.get("matched_pdfs") or []
        ground_truths = dspy_row.get("ground_truths") or []
        ground_truth = payload.get("ground_truth") or (ground_truths[0] if ground_truths else "") or test_case.get("ground_truth") or ""

        metric_values = {
            "dspy_total_score": deterministic_scores.get("total", ""),
            "dspy_keyword_score": deterministic_scores.get("keyword_presence", ""),
            "dspy_fallback_score": deterministic_scores.get("fallback_detection", ""),
            "dspy_format_score": deterministic_scores.get("formatting_constraints", ""),
            "dspy_pdf_grounding_score": deterministic_scores.get("pdf_grounding", ""),
            "ragas_answer_relevancy": ragas_row.get("answer_relevancy", ""),
            "ragas_answer_accuracy": ragas_row.get("answer_accuracy", ""),
            "ragas_faithfulness": ragas_row.get("faithfulness", ""),
            "ragas_context_precision": ragas_row.get("context_precision", ""),
            "ragas_context_utilization": ragas_row.get("context_utilization", ""),
            "ragas_context_recall": ragas_row.get("context_recall", ""),
            "ragas_context_relevance": ragas_row.get("context_relevance", ""),
            "ragas_response_groundedness": ragas_row.get("response_groundedness", ""),
            "ragas_context_entity_recall": ragas_row.get("context_entity_recall", ""),
            "ragas_noise_sensitivity_relevant": ragas_row.get("noise_sensitivity_relevant", ""),
            "ragas_noise_sensitivity_irrelevant": ragas_row.get("noise_sensitivity_irrelevant", ""),
        }

        issues = list(dspy_row.get("issues", []) or [])
        if not answer_text:
            issues.append("Bot answer was empty.")
        if dspy_row.get("source_match_status") == "matched_unexpected_pdf":
            issues.append("Observed evidence matched an unexpected PDF.")

        row: dict[str, Any] = {
            "test_id": test_id,
            "prompt": base_prompt or str(test_case.get("prompt") or payload.get("prompt") or ""),
            "answer_text": answer_text,
            "ground_truth": str(ground_truth),
        }

        metric_failures: list[str] = []
        for metric_name in metric_order:
            threshold = metric_thresholds[metric_name]
            operator = metric_operators.get(metric_name, ">=")
            metric_value = metric_values.get(metric_name, "")
            metric_result = _classify_metric_result(metric_value, threshold, operator=operator)
            metric_counters[metric_name][metric_result] += 1
            row[metric_name] = metric_value
            row[f"{metric_name}_pass_if{operator}"] = threshold
            row[f"{metric_name}_result"] = metric_result
            if metric_result == "FAIL":
                comparison_hint = ">" if operator == "<=" else "<"
                metric_failures.append(f"{metric_name} outside threshold ({metric_value} {comparison_hint} {threshold})")

        deduped_issues = list(dict.fromkeys(issue for issue in [*issues, *metric_failures] if issue))
        status = "FAIL" if deduped_issues else "PASS"
        failure_reason = " | ".join(deduped_issues)

        row["final_status"] = status
        row["status"] = status
        row["expected_pdfs"] = ", ".join(expected_pdfs) if expected_pdfs else ""
        row["matched_pdfs"] = ", ".join(matched_pdfs) if matched_pdfs else ""
        row["artifact_json_path"] = str(project_root / "artifacts" / "ui_runs" / f"{test_id}.json")
        results_rows.append(row)

        if status == "FAIL":
            failures_only_rows.append(
                {
                    "test_id": test_id,
                    "failure_reason": failure_reason,
                    "answer_text_excerpt": answer_text[:250],
                }
            )

    test_summary_rows = [
        {
            "evaluator": metric_name,
            "pass_rule": f"score {metric_operators.get(metric_name, '>=')} threshold",
            "pass_threshold": metric_thresholds[metric_name],
            "PASS": metric_counters[metric_name]["PASS"],
            "FAIL": metric_counters[metric_name]["FAIL"],
            "N/A": metric_counters[metric_name]["N/A"],
        }
        for metric_name in metric_order
    ]

    return results_rows, failures_only_rows, test_summary_rows, metric_thresholds


def _build_pdf_coverage_rows(project_root: Path, results_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry_path = project_root / "data" / "pdf_registry.json"
    registry = []
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))

    coverage_rows: list[dict[str, Any]] = []
    for record in registry:
        pdf_id = str(record.get("pdf_id") or "")
        pdf_name = str(record.get("pdf_name") or pdf_id)
        matching_rows = [row for row in results_rows if pdf_id and pdf_id in row.get("expected_pdfs", "")]
        total_tests = len(matching_rows)
        coverage_rows.append(
            {
                "pdf_name": pdf_name,
                "total_tests": total_tests,
                "tested": "YES" if total_tests > 0 else "NO",
            }
        )

    return coverage_rows


def _build_summary_rows(results_rows: list[dict[str, Any]], pdf_coverage_rows: list[dict[str, Any]], execution_timestamp: str) -> list[dict[str, Any]]:
    passed = sum(1 for row in results_rows if row.get("final_status", row.get("status")) == "PASS")
    failed = sum(1 for row in results_rows if row.get("final_status", row.get("status")) == "FAIL")
    total = len(results_rows)
    pass_rate = round((passed / total) * 100, 2) if total else 0.0
    return [
        {"metric": "total_tests", "value": total},
        {"metric": "passed", "value": passed},
        {"metric": "failed", "value": failed},
        {"metric": "pass_rate_percent", "value": pass_rate},
        {"metric": "untested_pdfs", "value": sum(1 for row in pdf_coverage_rows if row["tested"] == "NO")},
        {"metric": "execution_timestamp", "value": execution_timestamp},
        {"metric": "traceability", "value": "Each row maps to artifacts/ui_runs/<test_id>.json for the real chatbot answer."},
    ]


def _build_legend_rows(metric_thresholds: dict[str, float]) -> list[dict[str, Any]]:
    return [
        {"field": "prompt", "description": "The user question sent to the chatbot.", "importance": "Helps reviewers see exactly what was tested."},
        {"field": "answer_text", "description": "The real chatbot response captured from the UI.", "importance": "This is the business-visible answer for QA and audit review."},
        {"field": "ground_truth", "description": "The expected reference answer or expected behavior for the test case.", "importance": "Lets reviewers compare actual output with the intended expected outcome."},
        {"field": "final_status", "description": "Overall final test decision.", "importance": "Lets managers quickly see whether a test case passed or failed."},
        {"field": "dspy_total_score", "description": f"Combined deterministic DSPy score. Current threshold: {metric_thresholds['dspy_total_score']}", "importance": "Primary fast QA gate for structure, grounding, and expected response quality."},
        {"field": "dspy_keyword_score", "description": f"Checks whether required expected keywords appear in the answer. Current threshold: {metric_thresholds['dspy_keyword_score']}", "importance": "Confirms the answer addressed the expected topic or intent."},
        {"field": "dspy_fallback_score", "description": f"Checks whether fallback behavior is correct. Current threshold: {metric_thresholds['dspy_fallback_score']}", "importance": "Helps detect non-answers or incorrect fallback handling."},
        {"field": "dspy_format_score", "description": f"Checks formatting constraints and answer cleanliness. Current threshold: {metric_thresholds['dspy_format_score']}", "importance": "Important for readability and consistency in customer-facing responses."},
        {"field": "dspy_pdf_grounding_score", "description": f"Checks grounding against the expected PDF/document source. Current threshold: {metric_thresholds['dspy_pdf_grounding_score']}", "importance": "Important for auditability and source correctness."},
        {"field": "ragas_answer_relevancy", "description": f"Measures semantic relevance of the answer to the question. Current threshold: {metric_thresholds['ragas_answer_relevancy']}", "importance": "Validates that the response is on-topic."},
        {"field": "ragas_answer_accuracy", "description": f"NVIDIA-style LLM judge metric that compares the response against the reference answer. Current threshold: {metric_thresholds['ragas_answer_accuracy']}", "importance": "Useful for checking how closely the answer matches the expected ground truth."},
        {"field": "ragas_faithfulness", "description": f"Measures whether the answer stays faithful to the retrieved context. Current threshold: {metric_thresholds['ragas_faithfulness']}", "importance": "Useful for hallucination detection when context is available."},
        {"field": "ragas_context_precision", "description": f"Measures whether retrieved context chunks are relevant and ranked well. Current threshold: {metric_thresholds['ragas_context_precision']}", "importance": "Useful for checking retriever quality and ranking."},
        {"field": "ragas_context_utilization", "description": f"Measures whether the retrieved context is actually useful for generating the response. Current threshold: {metric_thresholds['ragas_context_utilization']}", "importance": "Useful when you want to judge whether the answer really used the retrieved evidence."},
        {"field": "ragas_context_recall", "description": f"Measures whether important supporting information was not missed in retrieval. Current threshold: {metric_thresholds['ragas_context_recall']}", "importance": "Useful for checking that the retriever did not miss important content."},
        {"field": "ragas_context_relevance", "description": f"NVIDIA-style metric that judges whether the retrieved contexts are relevant to the user input. Current threshold: {metric_thresholds['ragas_context_relevance']}", "importance": "Useful for a lightweight overall relevance check on retrieval quality."},
        {"field": "ragas_response_groundedness", "description": f"NVIDIA-style metric that checks how well the response is grounded in the retrieved context. Current threshold: {metric_thresholds['ragas_response_groundedness']}", "importance": "Useful for a token-efficient groundedness check similar to faithfulness."},
        {"field": "ragas_context_entity_recall", "description": f"Measures how many important entities from the reference are covered by the retrieved context. Current threshold: {metric_thresholds['ragas_context_entity_recall']}", "importance": "Useful for fact-heavy scenarios where retrieving the right named entities matters."},
        {"field": "ragas_noise_sensitivity_relevant", "description": f"Measures how often incorrect claims appear when using retrieved relevant context. Lower is better; pass if <= {metric_thresholds['ragas_noise_sensitivity_relevant']}", "importance": "Useful for checking whether the system is being misled into wrong answers even when relevant evidence is present."},
        {"field": "ragas_noise_sensitivity_irrelevant", "description": f"Measures how often incorrect claims appear due to irrelevant/noisy context. Lower is better; pass if <= {metric_thresholds['ragas_noise_sensitivity_irrelevant']}", "importance": "Useful for checking robustness against distractor or noisy retrieval."},
        {"field": "Green / Red / Yellow", "description": "Green = pass, Red = fail, Yellow = not available / skipped.", "importance": "Allows instant visual scanning of metric health."},
        {"field": "artifact_json_path", "description": "Path to the raw chatbot evidence JSON.", "importance": "Provides traceability for audit and root-cause analysis."},
    ]


def _style_workbook(excel_path: Path) -> None:
    workbook = load_workbook(excel_path)

    for sheet in workbook.worksheets:
        if sheet.max_row >= 1:
            sheet.freeze_panes = "A2"
            for cell in sheet[1]:
                cell.font = HEADER_FONT
                cell.fill = HEADER_FILL
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for column_index, column_cells in enumerate(sheet.iter_cols(1, sheet.max_column), start=1):
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            sheet.column_dimensions[get_column_letter(column_index)].width = min(max(max_length + 2, 14), 80)

    if "Test Results" in workbook.sheetnames:
        results_sheet = workbook["Test Results"]
        headers = {str(results_sheet.cell(row=1, column=index).value or ""): index for index in range(1, results_sheet.max_column + 1)}

        for row_index in range(2, results_sheet.max_row + 1):
            if "test_id" in headers:
                results_sheet.cell(row=row_index, column=headers["test_id"]).fill = BLUE_FILL

            if "final_status" in headers:
                status_cell = results_sheet.cell(row=row_index, column=headers["final_status"])
                if status_cell.value == "PASS":
                    status_cell.fill = GREEN_FILL
                elif status_cell.value == "FAIL":
                    status_cell.fill = RED_FILL

            for wrap_header in ["prompt", "answer_text", "ground_truth", "artifact_json_path"]:
                if wrap_header in headers:
                    results_sheet.cell(row=row_index, column=headers[wrap_header]).alignment = Alignment(wrap_text=True, vertical="top")

            for header, column_index in headers.items():
                if header.endswith("_result"):
                    cell = results_sheet.cell(row=row_index, column=column_index)
                    if cell.value == "PASS":
                        cell.fill = GREEN_FILL
                    elif cell.value == "FAIL":
                        cell.fill = RED_FILL
                    else:
                        cell.fill = YELLOW_FILL
                elif header.endswith("_pass_if>=") or header.endswith("_pass_if<="):
                    results_sheet.cell(row=row_index, column=column_index).fill = HEADER_FILL
                elif f"{header}_pass_if>=" in headers or f"{header}_pass_if<=" in headers:
                    score_cell = results_sheet.cell(row=row_index, column=column_index)
                    threshold_header = f"{header}_pass_if>=" if f"{header}_pass_if>=" in headers else f"{header}_pass_if<="
                    threshold_cell = results_sheet.cell(row=row_index, column=headers[threshold_header])
                    try:
                        score_value = _read_float(score_cell.value, 0.0)
                        threshold_value = _read_float(threshold_cell.value, 0.0)
                        if threshold_header.endswith("<="):
                            score_cell.fill = GREEN_FILL if score_value <= threshold_value else RED_FILL
                        else:
                            score_cell.fill = GREEN_FILL if score_value >= threshold_value else RED_FILL
                    except Exception:
                        if score_cell.value in (None, ""):
                            score_cell.fill = YELLOW_FILL

    if "Test Summary" in workbook.sheetnames:
        summary_sheet = workbook["Test Summary"]
        headers = {str(summary_sheet.cell(row=1, column=index).value or ""): index for index in range(1, summary_sheet.max_column + 1)}
        for row_index in range(2, summary_sheet.max_row + 1):
            if "PASS" in headers:
                summary_sheet.cell(row=row_index, column=headers["PASS"]).fill = GREEN_FILL
            if "FAIL" in headers:
                summary_sheet.cell(row=row_index, column=headers["FAIL"]).fill = RED_FILL
            if "N/A" in headers:
                summary_sheet.cell(row=row_index, column=headers["N/A"]).fill = YELLOW_FILL

    if "PDF Coverage" in workbook.sheetnames:
        coverage_sheet = workbook["PDF Coverage"]
        for cell in coverage_sheet["C"][1:]:
            if cell.value == "YES":
                cell.fill = GREEN_FILL
            elif cell.value == "NO":
                cell.fill = YELLOW_FILL

    if "Failures Only" in workbook.sheetnames:
        failures_sheet = workbook["Failures Only"]
        for row in failures_sheet.iter_rows(min_row=2, max_row=failures_sheet.max_row):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")

    if "Legend" in workbook.sheetnames:
        legend_sheet = workbook["Legend"]
        for row in legend_sheet.iter_rows(min_row=2, max_row=legend_sheet.max_row):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")

    workbook.save(excel_path)


def generate_enterprise_excel_report(
    project_root: str | Path,
    run_root: Path,
    dspy_results: dict[str, Any] | None = None,
    ragas_results: dict[str, Any] | None = None,
) -> Path:
    root = Path(project_root)
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    excel_path = reports_dir / "Latest_Report.xlsx"

    ui_artifacts = _load_ui_artifacts(run_root / "ui_runs")
    dspy_payload = dspy_results or _load_json(run_root / "dspy" / "dspy_results.json")
    ragas_payload = ragas_results or _load_json(run_root / "ragas" / "ragas_results.json")

    results_rows, failures_rows, test_summary_rows, metric_thresholds = _build_results_rows(root, ui_artifacts, dspy_payload, ragas_payload)
    pdf_coverage_rows = _build_pdf_coverage_rows(root, results_rows)
    summary_rows = _build_summary_rows(results_rows, pdf_coverage_rows, run_root.name)
    legend_rows = _build_legend_rows(metric_thresholds)

    results_columns = [
        "test_id",
        "prompt",
        "answer_text",
        "ground_truth",
        "final_status",
        "dspy_total_score",
        "dspy_total_score_pass_if>=",
        "dspy_total_score_result",
        "dspy_keyword_score",
        "dspy_keyword_score_pass_if>=",
        "dspy_keyword_score_result",
        "dspy_fallback_score",
        "dspy_fallback_score_pass_if>=",
        "dspy_fallback_score_result",
        "dspy_format_score",
        "dspy_format_score_pass_if>=",
        "dspy_format_score_result",
        "dspy_pdf_grounding_score",
        "dspy_pdf_grounding_score_pass_if>=",
        "dspy_pdf_grounding_score_result",
        "ragas_answer_relevancy",
        "ragas_answer_relevancy_pass_if>=",
        "ragas_answer_relevancy_result",
        "ragas_answer_accuracy",
        "ragas_answer_accuracy_pass_if>=",
        "ragas_answer_accuracy_result",
        "ragas_faithfulness",
        "ragas_faithfulness_pass_if>=",
        "ragas_faithfulness_result",
        "ragas_context_precision",
        "ragas_context_precision_pass_if>=",
        "ragas_context_precision_result",
        "ragas_context_utilization",
        "ragas_context_utilization_pass_if>=",
        "ragas_context_utilization_result",
        "ragas_context_recall",
        "ragas_context_recall_pass_if>=",
        "ragas_context_recall_result",
        "ragas_context_relevance",
        "ragas_context_relevance_pass_if>=",
        "ragas_context_relevance_result",
        "ragas_response_groundedness",
        "ragas_response_groundedness_pass_if>=",
        "ragas_response_groundedness_result",
        "ragas_context_entity_recall",
        "ragas_context_entity_recall_pass_if>=",
        "ragas_context_entity_recall_result",
        "ragas_noise_sensitivity_relevant",
        "ragas_noise_sensitivity_relevant_pass_if<=",
        "ragas_noise_sensitivity_relevant_result",
        "ragas_noise_sensitivity_irrelevant",
        "ragas_noise_sensitivity_irrelevant_pass_if<=",
        "ragas_noise_sensitivity_irrelevant_result",
        "expected_pdfs",
        "matched_pdfs",
        "artifact_json_path",
    ]

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pd.DataFrame(test_summary_rows, columns=["evaluator", "pass_rule", "pass_threshold", "PASS", "FAIL", "N/A"]).to_excel(
            writer,
            sheet_name="Test Summary",
            index=False,
        )
        pd.DataFrame(results_rows, columns=results_columns).to_excel(
            writer,
            sheet_name="Test Results",
            index=False,
        )
        pd.DataFrame(pdf_coverage_rows, columns=["pdf_name", "total_tests", "tested"]).to_excel(
            writer,
            sheet_name="PDF Coverage",
            index=False,
        )
        pd.DataFrame(failures_rows, columns=["test_id", "failure_reason", "answer_text_excerpt"]).to_excel(
            writer,
            sheet_name="Failures Only",
            index=False,
        )
        pd.DataFrame(summary_rows, columns=["metric", "value"]).to_excel(
            writer,
            sheet_name="Summary Dashboard",
            index=False,
        )
        pd.DataFrame(legend_rows, columns=["field", "description", "importance"]).to_excel(
            writer,
            sheet_name="Legend",
            index=False,
        )

    _style_workbook(excel_path)
    return excel_path


def create_enterprise_reporting_assets(
    project_root: str | Path,
    dspy_results: dict[str, Any] | None = None,
    ragas_results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(project_root)
    execution_timestamp = datetime.now(timezone.utc).strftime(RUN_FOLDER_FORMAT)
    run_root = root / "artifacts" / "reports" / execution_timestamp
    run_root.mkdir(parents=True, exist_ok=True)

    _copy_tree(root / "artifacts" / "ui_runs", run_root / "ui_runs")
    _copy_tree(root / "artifacts" / "dspy", run_root / "dspy")
    _copy_tree(root / "artifacts" / "ragas", run_root / "ragas")
    _copy_file_if_exists(root / "artifacts" / "reports" / "pytest_report.html", run_root / "system" / "pytest_report.html")
    _copy_file_if_exists(root / "artifacts" / "reports" / "compliance_audit.json", run_root / "system" / "compliance_audit.json")

    excel_path = generate_enterprise_excel_report(root, run_root, dspy_results=dspy_results, ragas_results=ragas_results)

    manifest = {
        "execution_timestamp": execution_timestamp,
        "run_root": str(run_root),
        "latest_excel_report": str(excel_path),
        "traceability_note": "Real chatbot responses are preserved in artifacts/reports/<timestamp>/ui_runs/<test_id>.json and mirrored in artifacts/ui_runs/<test_id>.json.",
    }
    (run_root / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest
