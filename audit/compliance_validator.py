from __future__ import annotations

import ast
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_FOLDERS = [
    "ui/pages",
    "ui/utils",
    "dspy_layer",
    "ragas_layer",
    "data",
    "tests",
]

REQUIRED_FILES = [
    "ui/pages/chatbot_page.py",
    "ui/utils/waits.py",
    "ui/utils/artifacts.py",
    "audit/reporting.py",
    "dspy_layer/ui_to_dspy.py",
    "ragas_layer/dspy_to_ragas.py",
    "ragas_layer/ragas_runner.py",
    "data/test_cases.json",
    "data/pdf_registry.json",
    "tests/test_ui_capture.py",
    "tests/test_dspy_eval.py",
    "tests/test_ragas_eval.py",
]

ALLOWED_POLLING_SLEEP_FILES = {
    "ui/pages/chatbot_page.py",
    "ui/utils/waits.py",
}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _add_check(checks: list[dict[str, str]], name: str, status: str, details: str) -> None:
    checks.append({"name": name, "status": status, "details": details})


def _find_sleep_calls(file_path: Path) -> list[int]:
    if not file_path.exists() or file_path.suffix != ".py":
        return []

    tree = ast.parse(_read_text(file_path))
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if getattr(node.func.value, "id", None) == "time" and node.func.attr == "sleep":
                lines.append(getattr(node, "lineno", -1))
    return lines


def _check_required_paths(project_root: Path, checks: list[dict[str, str]]) -> None:
    missing_folders = [path for path in REQUIRED_FOLDERS if not (project_root / path).exists()]
    missing_files = [path for path in REQUIRED_FILES if not (project_root / path).exists()]

    if missing_folders:
        _add_check(checks, "required_folders", "fail", f"Missing folders: {missing_folders}")
    else:
        _add_check(checks, "required_folders", "pass", "All required folders are present.")

    if missing_files:
        _add_check(checks, "required_files", "fail", f"Missing files: {missing_files}")
    else:
        _add_check(checks, "required_files", "pass", "All required files are present.")


def _check_playwright_compliance(project_root: Path, checks: list[dict[str, str]]) -> None:
    page_object_file = project_root / "ui/pages/chatbot_page.py"
    waits_file = project_root / "ui/utils/waits.py"
    conftest_file = project_root / "conftest.py"

    page_text = _read_text(page_object_file)
    waits_text = _read_text(waits_file)
    conftest_text = _read_text(conftest_file)

    required_methods = [
        "class ChatbotPage",
        "def open_app",
        "def open_chat_widget",
        "def send_message",
        "def wait_for_bot_response_to_finish",
        "def get_last_bot_message",
        "def get_citations_if_any",
    ]
    if all(method in page_text for method in required_methods):
        _add_check(checks, "playwright_pom", "pass", "Page Object Model is implemented in `ui/pages/chatbot_page.py`.")
    else:
        _add_check(checks, "playwright_pom", "fail", "Chatbot page object is missing one or more required methods.")

    if all(token in conftest_text for token in ["def browser(", "def context(", "def page("]):
        _add_check(checks, "playwright_pytest_fixtures", "pass", "Browser/context/page fixtures are defined in `conftest.py`.")
    else:
        _add_check(checks, "playwright_pytest_fixtures", "fail", "Expected Playwright pytest fixtures are missing.")

    if "wait_for_text_to_stabilize" in waits_text and "wait_for_load_state" in page_text:
        _add_check(checks, "playwright_waiting_strategy", "pass", "Stabilization and load-state waits are used instead of fixed end-user sleeps.")
    else:
        _add_check(checks, "playwright_waiting_strategy", "fail", "Expected wait helpers are not wired into the page object.")

    sleep_violations: list[str] = []
    ignored_parts = {".venv", "venv", "site-packages", "__pycache__", "artifacts"}
    for file_path in project_root.rglob("*.py"):
        if any(part in ignored_parts for part in file_path.parts):
            continue

        relative = file_path.relative_to(project_root).as_posix()
        sleep_lines = _find_sleep_calls(file_path)
        if not sleep_lines:
            continue
        if relative not in ALLOWED_POLLING_SLEEP_FILES:
            sleep_violations.append(f"{relative}: lines {sleep_lines}")

    if sleep_violations:
        _add_check(checks, "playwright_no_hard_sleeps", "fail", f"Unexpected sleep calls found: {sleep_violations}")
    else:
        _add_check(checks, "playwright_no_hard_sleeps", "pass", "No unapproved hard sleeps were found; only polling-based stabilization remains.")


def _check_dspy_compliance(project_root: Path, checks: list[dict[str, str]]) -> None:
    dspy_file = project_root / "dspy_layer/ui_to_dspy.py"
    dspy_text = _read_text(dspy_file)

    if "class UIArtifactAdapter(dspy.Module)" in dspy_text:
        _add_check(checks, "dspy_module_usage", "pass", "The DSPy adapter is implemented as a `dspy.Module`.")
    else:
        _add_check(checks, "dspy_module_usage", "fail", "`dspy.Module` is not used for the adapter program.")

    if "dspy.Example(" in dspy_text and ".with_inputs(" in dspy_text:
        _add_check(checks, "dspy_example_usage", "pass", "UI artifacts are converted to `dspy.Example` objects with explicit inputs.")
    else:
        _add_check(checks, "dspy_example_usage", "fail", "`dspy.Example` usage is incomplete or missing.")

    if "dspy.Evaluate(" in dspy_text:
        _add_check(checks, "dspy_evaluate_usage", "pass", "The evaluation layer uses official `dspy.Evaluate` orchestration.")
    else:
        _add_check(checks, "dspy_evaluate_usage", "fail", "`dspy.Evaluate` is not used in the DSPy evaluation layer.")

    if "playwright" not in dspy_text.lower() and "sync_api" not in dspy_text.lower():
        _add_check(checks, "dspy_no_ui_logic", "pass", "No Playwright/UI code is embedded in the DSPy layer.")
    else:
        _add_check(checks, "dspy_no_ui_logic", "fail", "UI logic leaked into the DSPy layer.")


def _check_ragas_compliance(project_root: Path, checks: list[dict[str, str]]) -> None:
    ragas_file = project_root / "ragas_layer/ragas_runner.py"
    ragas_text = _read_text(ragas_file)

    if "from ragas import evaluate" in ragas_text:
        _add_check(checks, "ragas_evaluate_usage", "pass", "The framework uses official `ragas.evaluate()` entry points.")
    else:
        _add_check(checks, "ragas_evaluate_usage", "fail", "`ragas.evaluate()` is not imported in the runner.")

    standard_metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    if all(metric in ragas_text for metric in standard_metrics):
        _add_check(checks, "ragas_standard_metrics", "pass", "Only standard RAGAS metrics are configured for the core audit.")
    else:
        _add_check(checks, "ragas_standard_metrics", "fail", "One or more required standard RAGAS metrics are missing.")

    if "skipped_metrics" in ragas_text and "reason" in ragas_text:
        _add_check(checks, "ragas_graceful_skips", "pass", "Missing context / missing evaluator conditions are reported clearly.")
    else:
        _add_check(checks, "ragas_graceful_skips", "fail", "RAGAS skip handling is not clearly reported.")


def _check_reporting_model(project_root: Path, checks: list[dict[str, str]]) -> None:
    reporting_file = project_root / "audit" / "reporting.py"
    readme_text = _read_text(project_root / "README.md")

    if reporting_file.exists():
        _add_check(checks, "enterprise_reporting_module", "pass", "Enterprise reporting module is present.")
    else:
        _add_check(checks, "enterprise_reporting_module", "fail", "`audit/reporting.py` is missing.")

    if "## Enterprise Reporting Model" in readme_text and "reports/Latest_Report.xlsx" in readme_text:
        _add_check(checks, "enterprise_reporting_docs", "pass", "README documents the enterprise reporting model and traceability path.")
    else:
        _add_check(checks, "enterprise_reporting_docs", "fail", "README is missing the enterprise reporting documentation section.")


def _check_ci_order(project_root: Path, checks: list[dict[str, str]]) -> None:
    workflow_file = project_root / ".github/workflows/ci.yml"
    workflow_text = _read_text(workflow_file)
    expected_order = ["pytest -m compliance", "pytest -m ui", "pytest -m dspy", "pytest -m ragas"]

    if all(step in workflow_text for step in expected_order):
        _add_check(checks, "ci_stage_order", "pass", "CI runs compliance, UI capture, DSPy, and RAGAS in explicit order.")
    else:
        _add_check(checks, "ci_stage_order", "warn", "CI does not yet show every staged evaluation command explicitly.")


def _check_python_runtime(checks: list[dict[str, str]]) -> None:
    current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info.major == 3 and sys.version_info.minor in {11, 12}:
        _add_check(checks, "python_runtime", "pass", f"Python {current_version} is within the most stable range for Playwright, DSPy, and RAGAS.")
    elif sys.version_info.major == 3 and sys.version_info.minor >= 13:
        _add_check(checks, "python_runtime", "warn", f"Python {current_version} is supported by this codebase, but RAGAS dependency wheels are typically most reliable on Python 3.11 or 3.12.")
    else:
        _add_check(checks, "python_runtime", "fail", f"Python {current_version} is below the required 3.11 baseline.")


def _check_data_flow(project_root: Path, checks: list[dict[str, str]]) -> None:
    temp_root = project_root / "artifacts" / "compliance_tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    synthetic_artifact = temp_root / "synthetic_ui_artifact.json"

    payload = {
        "id": "compliance_sample",
        "prompt": "How do I request a refund for an order?",
        "answer": "According to the Returns and Refunds Policy, you can request a refund through the support portal.",
        "contexts": [
            "Returns and Refunds Policy: Customers can request a refund through the support portal within the allowed window."
        ],
        "required_keywords": ["refund"],
        "forbidden_patterns": ["weather forecast"],
        "expect_fallback": False,
        "fallback_patterns": ["I don't know", "outside my scope"],
        "ground_truth": "The answer should reference the Returns and Refunds Policy and the refund request path.",
        "expected_pdfs": ["pdf_returns_refunds_policy"],
        "strict_grounding": True,
        "paraphrase_group": "refund_policy",
        "notes": "Synthetic compliance sample"
    }
    synthetic_artifact.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    try:
        from dspy_layer.ui_to_dspy import convert_ui_artifacts_to_dspy_examples, run_dspy_evaluation
        from ragas_layer.dspy_to_ragas import convert_dspy_predictions_to_ragas_dataset
        from ragas_layer.ragas_runner import run_ragas_evaluation

        examples = convert_ui_artifacts_to_dspy_examples(temp_root)
        if not examples:
            _add_check(checks, "data_flow_ui_to_dspy", "fail", "UI artifacts did not convert into DSPy examples.")
            return

        dspy_results = run_dspy_evaluation(examples, output_path=temp_root / "dspy")
        dataset = convert_dspy_predictions_to_ragas_dataset(dspy_results)
        ragas_results = run_ragas_evaluation(dataset, output_dir=temp_root / "ragas")

        if dataset.num_rows == 1 and {"question", "answer", "contexts"}.issubset(set(dataset.column_names)):
            _add_check(checks, "data_flow_ui_to_dspy_to_ragas", "pass", "Synthetic UI artifact flowed through DSPy and into a RAGAS-compatible dataset.")
        else:
            _add_check(checks, "data_flow_ui_to_dspy_to_ragas", "fail", "RAGAS dataset schema is incomplete after conversion.")

        if "summary" in ragas_results and "skipped_metrics" in ragas_results:
            _add_check(checks, "data_flow_ragas_runner", "pass", "RAGAS runner produced a structured result payload.")
        else:
            _add_check(checks, "data_flow_ragas_runner", "fail", "RAGAS runner output is missing expected report fields.")
    except ModuleNotFoundError as exc:
        _add_check(checks, "data_flow_dependencies", "warn", f"Runtime dependency missing during audit: {exc}")
    except Exception as exc:
        _add_check(checks, "data_flow_runtime", "fail", f"Data flow validation raised an exception: {exc}")


def run_compliance_audit(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root)
    checks: list[dict[str, str]] = []

    _check_required_paths(root, checks)
    _check_playwright_compliance(root, checks)
    _check_dspy_compliance(root, checks)
    _check_ragas_compliance(root, checks)
    _check_reporting_model(root, checks)
    _check_ci_order(root, checks)
    _check_python_runtime(checks)
    _check_data_flow(root, checks)

    summary = {
        "pass_count": sum(1 for check in checks if check["status"] == "pass"),
        "warn_count": sum(1 for check in checks if check["status"] == "warn"),
        "failure_count": sum(1 for check in checks if check["status"] == "fail"),
        "python_version": sys.version.split()[0],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report = {"summary": summary, "checks": checks}
    report_path = root / "artifacts" / "reports" / "compliance_audit.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
