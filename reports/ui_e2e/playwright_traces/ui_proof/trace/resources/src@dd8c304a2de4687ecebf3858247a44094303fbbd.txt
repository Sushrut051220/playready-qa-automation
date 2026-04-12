from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ui.utils.artifacts import save_run_artifact
from ui.utils.prompt_tracking import build_tracked_prompt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "ui_runs"


@pytest.mark.proof
@pytest.mark.flaky(reruns=1, reruns_delay=2)
def test_ui_proof_artifact(chatbot_page, request: pytest.FixtureRequest) -> None:
    base_url = os.getenv("BASE_URL", "").strip()
    if not base_url or "your-app.example.com" in base_url:
        pytest.fail("BASE_URL is not configured. Set a real BASE_URL in `.env` before running the live UI proof test.")

    request.node._artifact_test_id = "ui_proof"
    prompt = os.getenv("UI_PROOF_PROMPT", "What is Microsoft PlayReady?").strip()
    tracked_prompt = build_tracked_prompt(prompt, prefix="proof")
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

    artifact = {
        "test_id": "ui_proof",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "url": chatbot_page.get_current_url(),
        "prompt": tracked_prompt["base_prompt"],
        "prompt_sent": prompt_sent,
        "nonce_token": nonce,
        "run_id_visible_in_prompt": tracked_prompt["run_id_visible_in_prompt"],
        "answer_text": answer,
        "citations": citations,
        "observed_contexts": contexts,
        "browser_type": chatbot_page.get_browser_type(),
        "run_id": run_id,
        "network_capture": network_proof["status"],
        "network_capture_reason": network_proof.get("reason", ""),
        "network_proof": network_proof,
    }

    artifact_path = UI_ARTIFACT_DIR / "ui_proof" / "evidence.json"
    save_run_artifact(artifact, artifact_path)
    save_run_artifact(artifact, UI_ARTIFACT_DIR / "ui_proof" / f"{run_id}.json")

    assert answer.strip(), "Proof test captured an empty bot answer."
    assert artifact_path.exists(), f"Proof artifact was not created at {artifact_path}"

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["prompt"] == prompt, "Proof artifact does not contain the clean prompt."
    assert payload["prompt_sent"] == prompt_sent, "Proof artifact did not persist the sent prompt."
    assert payload["nonce_token"] == nonce, "Proof artifact did not persist the nonce token."
    assert payload["run_id"] == run_id, "Proof artifact did not persist the run ID."
