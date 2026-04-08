from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _is_truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_tracked_prompt(prompt: str, *, prefix: str = "") -> dict[str, Any]:
    clean_prompt = str(prompt or "").strip()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{prefix}_{timestamp}_{uuid4().hex[:8]}" if prefix else f"{timestamp}_{uuid4().hex[:8]}"
    nonce = f"[RUN:{run_id}]"
    append_run_id = _is_truthy(os.getenv("APPEND_RUN_ID_TO_PROMPT"), default=False)
    prompt_sent = f"{clean_prompt} {nonce}" if append_run_id else clean_prompt

    return {
        "run_id": run_id,
        "nonce_token": nonce,
        "base_prompt": clean_prompt,
        "prompt_sent": prompt_sent,
        "run_id_visible_in_prompt": append_run_id,
    }
