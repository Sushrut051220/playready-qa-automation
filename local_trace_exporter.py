"""
local_trace_exporter.py  (v2 - per-case routing)
=================================================
Writes nested span trees to standalone trace_*.json files AND keeps an in-memory
mapping (case_key -> trace dict) so the dashboard_bridge attach hook can
embed each trace into the matching testCase before writing test_run_*.json.
"""
from __future__ import annotations
import functools
import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _find_eval_history() -> Path:
    """Mirror the same discovery logic used by dashboard_bridge.py."""
    env_val = os.getenv("DEEPEVAL_RESULTS_FOLDER")
    if env_val:
        return Path(env_val)
    dashboard_names = ["deepeval-dashboard", "deepeval_dashboard"]
    search_roots = [
        Path(__file__).parent.parent,
        Path(__file__).parent.parent.parent,
        Path.home(),
    ]
    for root in search_roots:
        for name in dashboard_names:
            candidate = root / name
            if (candidate / "backend" / "main.py").exists():
                hist = candidate / "eval_history"
                hist.mkdir(parents=True, exist_ok=True)
                return hist
    fallback = Path(__file__).parent / "artifacts" / "eval_history"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback

_HIST = _find_eval_history()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(v: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "<truncated>"
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, (list, tuple)):
        return [_safe(x, depth + 1) for x in v[:20]]
    if isinstance(v, dict):
        return {str(k): _safe(val, depth + 1) for k, val in list(v.items())[:30]}
    try:
        return repr(v)[:500]
    except Exception:
        return "<unrepresentable>"


class _Span:
    __slots__ = ("id", "name", "type", "parent", "_start", "startTime", "endTime",
                 "durationMs", "status", "input", "output", "metadata", "error", "spans")

    def __init__(self, name: str, type_: str, parent):
        self.id = str(uuid.uuid4())
        self.name = name
        self.type = type_
        self.parent = parent
        self._start = time.perf_counter()
        self.startTime = _now_iso()
        self.endTime = None
        self.durationMs = 0
        self.status = "OK"
        self.input = None
        self.output = None
        self.metadata = {}
        self.error = None
        self.spans = []

    def finish(self) -> None:
        self.endTime = _now_iso()
        self.durationMs = int((time.perf_counter() - self._start) * 1000)

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "startTime": self.startTime,
            "endTime": self.endTime,
            "durationMs": self.durationMs,
            "input": _safe(self.input),
            "output": _safe(self.output),
            "metadata": self.metadata,
            "spans": [s.to_dict() for s in self.spans],
            "children": [s.to_dict() for s in self.spans],
        }
        if self.error:
            d["error"] = self.error
        return d


class LocalTracer:
    """Thread-unsafe but adequate for sequential RAGAS evaluation."""

    def __init__(self) -> None:
        self._stack: list = []
        self._pending_by_case: dict = {}
        self._current_case_key = None
        try:
            _HIST.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def set_case_key(self, key) -> None:
        """Tag the next root trace with this case key so the bridge can attach
        the matching trace to the correct testCase in the dashboard JSON."""
        self._current_case_key = str(key) if key is not None else None

    @contextmanager
    def span(self, name: str, type: str = "task", input: Any = None,
             metadata: dict | None = None, case_key: str | None = None):
        parent = self._stack[-1] if self._stack else None
        s = _Span(name, type, parent)
        if input is not None:
            s.input = input
        if metadata:
            s.metadata.update(metadata)
        if parent is not None:
            parent.spans.append(s)
        self._stack.append(s)
        try:
            yield s
        except Exception as e:
            s.status = "ERROR"
            s.error = repr(e)[:500]
            raise
        finally:
            s.finish()
            self._stack.pop()
            if parent is None:
                d = s.to_dict()
                key = case_key or self._current_case_key
                if key:
                    self._pending_by_case[str(key)] = d
                self._flush_root(d, key)

    def observe(self, type: str = "task", name: str | None = None):
        def deco(fn):
            span_name = name or fn.__name__

            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                with self.span(span_name, type=type,
                               input={"args_count": len(args),
                                      "kwargs_keys": list(kwargs.keys())}) as s:
                    out = fn(*args, **kwargs)
                    s.output = _safe(out)
                    return out
            return wrapper
        return deco

    def _flush_root(self, root_dict: dict, case_key) -> None:
        fname = f"trace_{int(time.time())}_{root_dict['id'][:8]}.json"
        payload = {
            "id": root_dict["id"],
            "name": root_dict["name"],
            "status": root_dict["status"],
            "startTime": root_dict["startTime"],
            "endTime": root_dict["endTime"],
            "durationMs": root_dict["durationMs"],
            "traces": [root_dict],
            "spans":  [root_dict],
            "case_key": case_key,
            "hyperparameters": {
                "project": "playready",
                "source": "local-tracer",
            },
        }
        try:
            (_HIST / fname).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[trace] write failed: {e}")


_tracer = None


def get_tracer() -> LocalTracer:
    global _tracer
    if _tracer is None:
        _tracer = LocalTracer()
    return _tracer
