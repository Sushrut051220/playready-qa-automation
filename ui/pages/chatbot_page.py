from __future__ import annotations

import json
import os
import time
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ui.utils.waits import wait_for_text_to_stabilize


DEFAULT_SELECTORS: dict[str, tuple[str, str]] = {
    # Replace these defaults in `.env` to match your actual application.
    "widget_button": ("CHAT_WIDGET_BUTTON_SELECTOR", '[data-testid="chat-widget-button"]'),
    "iframe": ("CHAT_IFRAME_SELECTOR", ""),
    "chat_input": ("CHAT_INPUT_SELECTOR", 'textarea[data-testid="chat-input"]'),
    "send_button": ("CHAT_SEND_BUTTON_SELECTOR", 'button[data-testid="chat-send"]'),
    "bot_message": ("BOT_MESSAGE_SELECTOR", '[data-testid="bot-message"]'),
    "user_message": ("USER_MESSAGE_SELECTOR", '[data-testid="user-message"]'),
    "spinner": ("CHAT_STREAMING_INDICATOR_SELECTOR", '[data-testid="chat-streaming"]'),
    "citation": ("CHAT_CITATION_SELECTOR", '[data-testid="chat-citation"]'),
    "chat_api_url_contains": ("CHAT_API_URL_CONTAINS", "/chat|/message|/conversation"),
    "network_keyword": ("NETWORK_CONTEXT_URL_KEYWORD", "/api/chat"),
}


class ChatbotPage:
    """Page object for an embedded RAG chatbot widget in a web application."""

    def __init__(self, page: Page, base_url: str | None = None, timeout_ms: int | None = None) -> None:
        self.page = page
        self.base_url = (base_url or os.getenv("BASE_URL", "")).strip()
        self.timeout_ms = int(timeout_ms or os.getenv("TIMEOUT_MS", "30000"))
        self.response_stable_ms = int(os.getenv("RESPONSE_STABLE_MS", "1200"))
        self.capture_network_contexts_enabled = os.getenv("CAPTURE_NETWORK_CONTEXTS", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.selectors = {
            key: os.getenv(env_name, default).strip() for key, (env_name, default) in DEFAULT_SELECTORS.items()
        }
        self._network_contexts: list[str] = []
        self._network_events: list[dict[str, Any]] = []
        self._network_capture_status = "not_started"
        self._network_capture_reason = ""
        self._last_prompt_sent = ""
        self._bot_messages_before_send = 0
        self._last_bot_text_before_send = ""
        self._register_network_listeners()

    def _register_network_listeners(self) -> None:
        if not self.capture_network_contexts_enabled:
            self._network_capture_status = "disabled"
            self._network_capture_reason = "CAPTURE_NETWORK_CONTEXTS is disabled in the environment."
            return

        self._network_capture_status = "listening"

        def handle_request(request) -> None:
            if not self._url_matches_capture_pattern(request.url):
                return

            try:
                payload_attr = getattr(request, "post_data", None)
                payload = payload_attr() if callable(payload_attr) else payload_attr
                if not payload:
                    json_attr = getattr(request, "post_data_json", None)
                    payload = json_attr() if callable(json_attr) else json_attr
            except Exception:
                payload = None

            self._network_events.append(
                {
                    "type": "request",
                    "url": request.url,
                    "method": request.method,
                    "payload": self._serialize_network_payload(payload),
                }
            )
            self._network_capture_status = "captured"

        def handle_response(response) -> None:
            if not self._url_matches_capture_pattern(response.url):
                return

            payload: Any = None
            try:
                content_type = (response.headers or {}).get("content-type", "").lower()
                if "json" in content_type:
                    payload = response.json()
                else:
                    payload = response.text()
            except Exception as exc:
                payload = {"unavailable": str(exc)}

            self._network_events.append(
                {
                    "type": "response",
                    "url": response.url,
                    "status": response.status,
                    "payload": self._serialize_network_payload(payload),
                }
            )
            self._network_capture_status = "captured"

            extracted = self._extract_candidate_contexts(payload)
            if extracted:
                self._network_contexts.extend(extracted)
                self._network_contexts = self._dedupe(self._network_contexts)

        def handle_websocket(websocket) -> None:
            if self._network_capture_status != "captured":
                self._network_capture_status = "ws_not_supported"
                self._network_capture_reason = (
                    f"WebSocket detected at {websocket.url}; frame payload capture is not enabled in this lightweight harness."
                )

        self.page.on("request", handle_request)
        self.page.on("response", handle_response)
        self.page.on("websocket", handle_websocket)

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            cleaned = " ".join(str(item).split()).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                ordered.append(cleaned)
        return ordered

    @staticmethod
    def _serialize_network_payload(payload: Any, max_length: int = 3000) -> str:
        if payload is None:
            return ""
        if isinstance(payload, (dict, list)):
            serialized = json.dumps(payload, ensure_ascii=False)
        else:
            serialized = str(payload)
        normalized = " ".join(serialized.split()).strip()
        return normalized[:max_length]

    def _url_matches_capture_pattern(self, url: str) -> bool:
        configured = self.selectors.get("chat_api_url_contains", "") or self.selectors.get("network_keyword", "")
        patterns = [item.strip() for item in configured.split("|") if item.strip()]
        if not patterns:
            return True
        return any(pattern.lower() in url.lower() for pattern in patterns)

    def _extract_candidate_contexts(self, payload: Any) -> list[str]:
        keys_of_interest = {
            "context",
            "contexts",
            "citation",
            "citations",
            "source",
            "sources",
            "chunk",
            "chunks",
            "passage",
            "passages",
            "document",
            "documents",
            "retrieved_contexts",
            "snippets",
        }

        found: list[str] = []

        if isinstance(payload, dict):
            for key, value in payload.items():
                if str(key).lower() in keys_of_interest:
                    found.extend(self._coerce_text_list(value))
                else:
                    found.extend(self._extract_candidate_contexts(value))
        elif isinstance(payload, list):
            for item in payload:
                found.extend(self._extract_candidate_contexts(item))

        return self._dedupe(found)

    def _coerce_text_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            collected: list[str] = []
            for item in value:
                collected.extend(self._coerce_text_list(item))
            return collected
        if isinstance(value, dict):
            preferred_fields = ["text", "content", "page_content", "snippet", "title", "body"]
            for field in preferred_fields:
                if field in value and isinstance(value[field], str):
                    return [value[field]]
            collected: list[str] = []
            for nested_value in value.values():
                collected.extend(self._coerce_text_list(nested_value))
            return collected
        return [str(value)]

    def _scope(self):
        iframe_selector = self.selectors.get("iframe", "")
        if iframe_selector:
            return self.page.frame_locator(iframe_selector)
        return self.page

    def _is_input_visible(self) -> bool:
        try:
            return self._scope().locator(self.selectors["chat_input"]).first.is_visible()
        except Exception:
            return False

    def _scroll_into_view(self, locator) -> None:
        try:
            locator.scroll_into_view_if_needed(timeout=min(2000, self.timeout_ms))
        except Exception:
            pass

    def open_app(self) -> None:
        if not self.base_url:
            raise ValueError("BASE_URL is empty. Set it in your environment or .env file.")

        self.page.goto(self.base_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        try:
            self.page.wait_for_load_state("networkidle", timeout=min(5000, self.timeout_ms))
        except PlaywrightTimeoutError:
            # Some modern apps keep background network calls open; this is acceptable.
            pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        retry=retry_if_exception_type((AssertionError, PlaywrightError, PlaywrightTimeoutError)),
        reraise=True,
    )
    def open_chat_widget(self) -> None:
        if self._is_input_visible():
            input_box = self._scope().locator(self.selectors["chat_input"]).first
            self._scroll_into_view(input_box)
            return

        widget_button = self.page.locator(self.selectors["widget_button"]).first
        widget_button.wait_for(state="visible", timeout=self.timeout_ms)
        self._scroll_into_view(widget_button)
        widget_button.click(timeout=self.timeout_ms)

        input_box = self._scope().locator(self.selectors["chat_input"]).first
        input_box.wait_for(state="visible", timeout=self.timeout_ms)
        self._scroll_into_view(input_box)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        retry=retry_if_exception_type((AssertionError, PlaywrightError, PlaywrightTimeoutError)),
        reraise=True,
    )
    def send_message(self, prompt: str) -> None:
        self._network_contexts.clear()
        self._network_events.clear()
        self._network_capture_status = "listening"
        self._network_capture_reason = ""
        self._last_prompt_sent = prompt

        scope = self._scope()
        bot_messages = scope.locator(self.selectors["bot_message"])
        self._bot_messages_before_send = bot_messages.count()
        self._last_bot_text_before_send = ""

        if self._bot_messages_before_send:
            try:
                self._last_bot_text_before_send = " ".join(bot_messages.last.inner_text(timeout=1000).split())
            except PlaywrightError:
                self._last_bot_text_before_send = ""

        input_box = scope.locator(self.selectors["chat_input"]).first
        input_box.wait_for(state="visible", timeout=self.timeout_ms)
        self._scroll_into_view(input_box)
        input_box.click(timeout=self.timeout_ms)

        try:
            input_box.fill(prompt, timeout=self.timeout_ms)
        except PlaywrightError:
            # Some apps use contenteditable divs instead of input/textarea.
            self.page.keyboard.press("Control+A")
            self.page.keyboard.insert_text(prompt)

        send_button = scope.locator(self.selectors["send_button"]).first
        try:
            if send_button.is_visible():
                send_button.click(timeout=self.timeout_ms)
            else:
                input_box.press("Enter", timeout=self.timeout_ms)
        except Exception:
            input_box.press("Enter", timeout=self.timeout_ms)

    def wait_for_bot_response_to_finish(self) -> str:
        scope = self._scope()
        bot_messages = scope.locator(self.selectors["bot_message"])
        deadline = time.monotonic() + (self.timeout_ms / 1000)

        while time.monotonic() < deadline:
            count = bot_messages.count()
            current_text = ""
            if count:
                try:
                    current_text = " ".join(bot_messages.last.inner_text(timeout=500).split())
                except PlaywrightError:
                    current_text = ""

            if count > self._bot_messages_before_send or (
                current_text and current_text != self._last_bot_text_before_send
            ):
                break
            time.sleep(0.2)
        else:
            raise TimeoutError("No new bot response was detected after sending the message.")

        self._scroll_into_view(bot_messages.last)

        spinner = scope.locator(self.selectors["spinner"]).first
        try:
            spinner.wait_for(state="hidden", timeout=min(5000, self.timeout_ms))
        except PlaywrightTimeoutError:
            # Spinner may not exist or may not be implemented in the target UI.
            pass
        except PlaywrightError:
            pass

        stabilized_text = wait_for_text_to_stabilize(
            bot_messages.last,
            stable_ms=self.response_stable_ms,
            timeout_ms=self.timeout_ms,
        )
        self._scroll_into_view(bot_messages.last)

        try:
            self.page.wait_for_load_state("networkidle", timeout=2000)
        except PlaywrightTimeoutError:
            pass

        return stabilized_text

    def get_last_bot_message(self) -> str:
        last_message = self._scope().locator(self.selectors["bot_message"]).last
        self._scroll_into_view(last_message)
        return " ".join(last_message.inner_text(timeout=self.timeout_ms).split()).strip()

    def get_citations_if_any(self) -> list[str]:
        citations_locator = self._scope().locator(self.selectors["citation"])
        try:
            count = citations_locator.count()
        except PlaywrightError:
            return []

        if count == 0:
            return []

        texts: list[str] = []
        for index in range(count):
            try:
                item_text = citations_locator.nth(index).inner_text(timeout=1000).strip()
                if item_text:
                    texts.append(item_text)
            except PlaywrightError:
                continue

        return self._dedupe(texts)

    def capture_contexts_from_network(self) -> list[str]:
        """Return contexts extracted from network responses, if the app exposes them."""
        return self._dedupe(self._network_contexts)

    def get_current_url(self) -> str:
        return self.page.url

    def get_browser_type(self) -> str:
        try:
            browser = self.page.context.browser
            if browser and getattr(browser, "browser_type", None):
                return str(browser.browser_type.name)
        except Exception:
            pass
        return "chromium"

    def get_network_proof(self, nonce: str | None = None) -> dict[str, Any]:
        request_events = [event for event in self._network_events if event.get("type") == "request"]
        response_events = [event for event in self._network_events if event.get("type") == "response"]
        nonce_in_request_payload = bool(
            nonce and any(nonce in str(event.get("payload", "")) for event in request_events)
        )

        status = self._network_capture_status
        reason = self._network_capture_reason
        if status == "listening" and not self._network_events:
            status = "not_observed"
            reason = (
                "No matching HTTP request/response was captured for the configured CHAT_API_URL_CONTAINS pattern. "
                "If the widget uses WebSockets, the harness records that as best-effort only."
            )

        return {
            "status": status,
            "reason": reason,
            "request_events": request_events,
            "response_events": response_events,
            "nonce_in_request_payload": nonce_in_request_payload,
            "prompt_preview": self._last_prompt_sent,
        }
