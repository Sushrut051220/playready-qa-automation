from __future__ import annotations

import time

from playwright.sync_api import Error as PlaywrightError


def wait_for_text_to_stabilize(locator, stable_ms: int = 1200, timeout_ms: int = 30000) -> str:
    """Wait until a locator's text stops changing for a stable window.

    This is useful for chatbot responses that stream token-by-token.
    """
    deadline = time.monotonic() + (timeout_ms / 1000)
    last_text = ""
    stable_since = None
    last_non_empty = ""

    while time.monotonic() < deadline:
        try:
            current_text = " ".join(locator.inner_text(timeout=1000).split())
        except PlaywrightError:
            time.sleep(0.2)
            continue

        if current_text:
            last_non_empty = current_text

        if current_text and current_text == last_text:
            if stable_since is None:
                stable_since = time.monotonic()
            elif (time.monotonic() - stable_since) * 1000 >= stable_ms:
                return current_text
        else:
            last_text = current_text
            stable_since = time.monotonic() if current_text else None

        time.sleep(0.2)

    if last_non_empty:
        return last_non_empty

    raise TimeoutError(
        f"Text did not stabilize within {timeout_ms} ms for locator: {locator}"
    )
