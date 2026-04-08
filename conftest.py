from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from ui.pages.chatbot_page import ChatbotPage
from ui.utils.artifacts import attach_screenshot_on_failure, attach_trace_on_failure, get_test_artifact_dir


PROJECT_ROOT = Path(__file__).resolve().parent
ARTIFACT_DIRS = [
    PROJECT_ROOT / "artifacts" / "ui_runs",
    PROJECT_ROOT / "artifacts" / "dspy",
    PROJECT_ROOT / "artifacts" / "ragas",
    PROJECT_ROOT / "artifacts" / "reports",
    PROJECT_ROOT / "artifacts" / "screenshots",
    PROJECT_ROOT / "artifacts" / "traces",
]


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    for directory in ARTIFACT_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def settings() -> dict[str, Any]:
    return {
        "base_url": os.getenv("BASE_URL", "").strip(),
        "headless": os.getenv("HEADLESS", "true").lower() in {"1", "true", "yes", "on"},
        "timeout_ms": int(os.getenv("TIMEOUT_MS", "30000")),
        "browser_channel": os.getenv("PLAYWRIGHT_BROWSER_CHANNEL", "").strip(),
        "trace_always": os.getenv("TRACE_ALWAYS", "false").lower() in {"1", "true", "yes", "on"},
    }


@pytest.fixture(scope="session")
def playwright_instance() -> Playwright:
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright, settings: dict[str, Any]) -> Browser:
    launch_options: dict[str, Any] = {
        "headless": bool(settings["headless"]),
        "args": ["--start-maximized"],
    }
    browser_channel = str(settings.get("browser_channel", "") or "")
    if browser_channel:
        launch_options["channel"] = browser_channel

    try:
        browser = playwright_instance.chromium.launch(**launch_options)
    except Exception as exc:
        if not browser_channel and os.name == "nt" and "EFTYPE" in str(exc):
            launch_options["channel"] = "chrome"
            browser = playwright_instance.chromium.launch(**launch_options)
        else:
            raise

    yield browser
    browser.close()


@pytest.fixture()
def context(browser: Browser, request: pytest.FixtureRequest, settings: dict[str, Any]) -> BrowserContext:
    context_options: dict[str, Any] = {"ignore_https_errors": True}
    if bool(settings["headless"]):
        context_options["viewport"] = {"width": 1440, "height": 900}
    else:
        context_options["no_viewport"] = True

    context = browser.new_context(**context_options)
    context.set_default_timeout(int(settings["timeout_ms"]))
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    request.node._browser_context = context
    yield context

    rep_call = getattr(request.node, "rep_call", None)
    artifact_test_id = getattr(request.node, "_artifact_test_id", request.node.name)
    artifact_dir = get_test_artifact_dir(PROJECT_ROOT / "artifacts" / "ui_runs", artifact_test_id)
    should_persist_trace = bool(settings.get("trace_always")) or bool(rep_call and rep_call.failed)

    if should_persist_trace:
        attach_trace_on_failure(context, artifact_test_id, output_dir=artifact_dir, file_name="trace.zip")
    else:
        try:
            context.tracing.stop()
        except Exception:
            pass
    context.close()


@pytest.fixture()
def page(context: BrowserContext, request: pytest.FixtureRequest, settings: dict[str, Any]) -> Page:
    page = context.new_page()
    request.node._page = page
    yield page

    rep_call = getattr(request.node, "rep_call", None)
    artifact_test_id = getattr(request.node, "_artifact_test_id", request.node.name)
    artifact_dir = get_test_artifact_dir(PROJECT_ROOT / "artifacts" / "ui_runs", artifact_test_id)
    should_persist_screenshot = bool(settings.get("trace_always")) or bool(rep_call and rep_call.failed)
    if should_persist_screenshot:
        attach_screenshot_on_failure(page, artifact_test_id, output_dir=artifact_dir, file_name="screenshot.png")
    page.close()


@pytest.fixture()
def chatbot_page(page: Page, settings: dict[str, Any]) -> ChatbotPage:
    return ChatbotPage(page=page, base_url=str(settings["base_url"]), timeout_ms=int(settings["timeout_ms"]))


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)
