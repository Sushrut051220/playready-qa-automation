from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def save_run_artifact(json_obj: dict[str, Any], path: str | Path) -> Path:
    """Persist a JSON artifact for later DSPy / RAGAS processing."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file_handle:
        json.dump(json_obj, file_handle, indent=2, ensure_ascii=False)
    return target


def get_test_artifact_dir(root_dir: str | Path, test_name: str) -> Path:
    target_dir = Path(root_dir) / _safe_name(test_name)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def attach_screenshot_on_failure(
    page,
    test_name: str,
    output_dir: str | Path = "artifacts/screenshots",
    file_name: str | None = None,
) -> Path | None:
    """Capture a screenshot when a UI test fails or when trace evidence is always enabled."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / (file_name or f"{_safe_name(test_name)}.png")

    try:
        page.screenshot(path=str(target_file), full_page=True)
        return target_file
    except Exception:
        return None


def attach_trace_on_failure(
    browser_context,
    test_name: str,
    output_dir: str | Path = "artifacts/traces",
    file_name: str | None = None,
) -> Path | None:
    """Stop Playwright tracing and persist a trace zip on failure or when trace evidence is always enabled."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / (file_name or f"{_safe_name(test_name)}_trace.zip")

    try:
        browser_context.tracing.stop(path=str(target_file))
        return target_file
    except Exception:
        return None
