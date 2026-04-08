from __future__ import annotations

from ui.utils.prompt_tracking import build_tracked_prompt


def test_build_tracked_prompt_hides_run_id_by_default(monkeypatch) -> None:
    monkeypatch.delenv("APPEND_RUN_ID_TO_PROMPT", raising=False)

    tracked = build_tracked_prompt("What is Microsoft PlayReady?")

    assert tracked["prompt_sent"] == "What is Microsoft PlayReady?"
    assert tracked["base_prompt"] == "What is Microsoft PlayReady?"
    assert tracked["run_id_visible_in_prompt"] is False
    assert tracked["nonce_token"].startswith("[RUN:")
    assert tracked["run_id"] in tracked["nonce_token"]


def test_build_tracked_prompt_can_show_run_id_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("APPEND_RUN_ID_TO_PROMPT", "true")

    tracked = build_tracked_prompt("What is Microsoft PlayReady?")

    assert tracked["run_id_visible_in_prompt"] is True
    assert tracked["nonce_token"] in tracked["prompt_sent"]
