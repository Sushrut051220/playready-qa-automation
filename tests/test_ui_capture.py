from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ui.utils.artifacts import save_run_artifact
from ui.utils.prompt_tracking import build_tracked_prompt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_CASES_FILE = PROJECT_ROOT / "data" / "test_cases.json"
UI_ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "ui_runs"


def load_test_cases() -> list[dict]:
    return json.loads(TEST_CASES_FILE.read_text(encoding="utf-8"))


@pytest.mark.ui
@pytest.mark.regression
@pytest.mark.flaky(reruns=1, reruns_delay=2)
@pytest.mark.parametrize("case_data", load_test_cases(), ids=lambda case: case["id"])
def test_capture_chatbot_output(chatbot_page, case_data: dict, request: pytest.FixtureRequest) -> None:
    base_url = os.getenv("BASE_URL", "").strip()
    if not base_url or "your-app.example.com" in base_url:
        pytest.skip("Set a real BASE_URL in `.env` before running the UI chatbot stage.")

    request.node._artifact_test_id = case_data["id"]
    tracked_prompt = build_tracked_prompt(case_data["prompt"])
    prompt_sent = tracked_prompt["prompt_sent"]
    nonce = tracked_prompt["nonce_token"]
    run_id = tracked_prompt["run_id"]

    chatbot_page.open_app()
    chatbot_page.open_chat_widget()
    chatbot_page.send_message(prompt_sent)
    chatbot_page.wait_for_bot_response_to_finish()

    answer = chatbot_page.get_last_bot_message()
    citations = chatbot_page.get_citations_if_any()
    contexts = citations or chatbot_page.capture_contexts_from_network()
    network_proof = chatbot_page.get_network_proof(nonce=nonce)

    print(f"\n--- UI Capture: {case_data['id']} ---")
    print(f"Run ID: {run_id}")
    print(f"Prompt: {tracked_prompt['base_prompt']}")
    print(f"Answer: {answer}")
    print(f"Citations: {citations}")
    print(f"Contexts: {contexts}")
    print(
        f"Network proof: {network_proof['status']} | nonce_in_request={network_proof['nonce_in_request_payload']}"
    )
    if network_proof.get("reason"):
        print(f"Network note: {network_proof['reason']}")

    artifact = {
        "id": case_data["id"],
        "test_id": case_data["id"],
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "url": chatbot_page.get_current_url(),
        "prompt": tracked_prompt["base_prompt"],
        "base_prompt": tracked_prompt["base_prompt"],
        "prompt_sent": prompt_sent,
        "nonce_token": nonce,
        "run_id_visible_in_prompt": tracked_prompt["run_id_visible_in_prompt"],
        "answer": answer,
        "answer_text": answer,
        "citations": citations,
        "contexts": contexts,
        "observed_contexts": contexts,
        "browser_type": chatbot_page.get_browser_type(),
        "network_capture": network_proof["status"],
        "network_capture_reason": network_proof.get("reason", ""),
        "network_request_payloads": [event.get("payload", "") for event in network_proof.get("request_events", [])],
        "network_response_payloads": [event.get("payload", "") for event in network_proof.get("response_events", [])],
        "network_proof": network_proof,
        "required_keywords": case_data.get("required_keywords", []),
        "forbidden_patterns": case_data.get("forbidden_patterns", []),
        "expect_fallback": case_data.get("expect_fallback", False),
        "fallback_patterns": case_data.get("fallback_patterns", []),
        "ground_truth": case_data.get("ground_truth"),
        "expected_pdfs": case_data.get("expected_pdfs", []),
        "strict_grounding": case_data.get("strict_grounding", False),
        "paraphrase_group": case_data.get("paraphrase_group"),
        "notes": case_data.get("notes"),
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    save_run_artifact(artifact, UI_ARTIFACT_DIR / f"{case_data['id']}.json")
    save_run_artifact(artifact, UI_ARTIFACT_DIR / case_data["id"] / "evidence.json")
    save_run_artifact(artifact, UI_ARTIFACT_DIR / case_data["id"] / f"{run_id}.json")

    failures: list[str] = []
    if not answer.strip():
        failures.append("Bot answer was empty.")

    assert not failures, " | ".join(failures)
