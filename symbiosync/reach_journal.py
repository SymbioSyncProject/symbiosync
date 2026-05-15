"""
Local Reach Journal store.

The journal records accountable touch/reach events as dyad feedback artifacts,
not as raw BLE/debug dumps and not as a full activation journal.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReachJournal:
    """Small JSONL-backed reach-event store.

    Events are keyed by the server-generated request_id. Response-note edits
    rewrite the JSONL file. This is intentionally simple for v0.1 local state.
    """

    def __init__(self, path: Path, max_events: int = 1000):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_events = max_events
        self._lock = RLock()
        self._events: list[dict[str, Any]] = []
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        events: list[dict[str, Any]] = []
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict) and event.get("request_id"):
                    events.append(event)
        except OSError:
            return
        self._events = events[-self.max_events:]

    def _write_all(self):
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        lines = [json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in self._events]
        tmp.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        tmp.replace(self.path)

    def _find_index(self, request_id: str) -> int | None:
        for i, event in enumerate(self._events):
            if event.get("request_id") == request_id:
                return i
        return None

    @staticmethod
    def _sanitize_params(params: dict | None) -> dict:
        if not isinstance(params, dict):
            return {}
        # Keep human-readable request shape. Do not add raw BLE/protocol payloads.
        return dict(params)

    @staticmethod
    def _result_summary(result: Any) -> dict:
        """Store only request-result truth fields, not raw protocol chatter."""
        if not isinstance(result, dict):
            return {"stage": "unknown", "truth_note": "Non-dict result from request path."}

        if "stage" in result or "ok" in result:
            return {
                "ok": result.get("ok"),
                "stage": result.get("stage", "unknown"),
                "truth_note": result.get("truth_note", ""),
                "error": result.get("error", ""),
                "transport": result.get("transport"),
                "hardware_ack": result.get("hardware_ack"),
                "observed_effect": result.get("observed_effect"),
            }

        per_device = {}
        failed = 0
        for addr, item in result.items():
            if isinstance(item, dict):
                summary = ReachJournal._result_summary(item)
                per_device[addr] = summary
                if summary.get("ok") is False:
                    failed += 1
        return {
            "ok": bool(per_device) and failed == 0,
            "stage": "multi_device_result" if failed == 0 else "one_or_more_failed",
            "truth_note": "Per-device results are request/transport results, not observed body state.",
            "per_device": per_device,
        }

    def record_request(self, envelope: dict) -> dict:
        request_id = envelope.get("request_id")
        if not request_id:
            raise ValueError("reach event requires request_id")
        event = {
            "request_id": request_id,
            "received_at": envelope.get("received_at") or _utc_now(),
            "updated_at": _utc_now(),
            "source_channel": envelope.get("source_channel", "unknown"),
            "actor": envelope.get("actor", "Unknown"),
            "actor_trust": envelope.get("actor_trust", "self_reported"),
            "target_address": envelope.get("target_address", ""),
            "target_alias": envelope.get("target_alias", envelope.get("target_address", "")),
            "request": envelope.get("request", ""),
            "request_params": self._sanitize_params(envelope.get("request_params")),
            "note": envelope.get("note", ""),
            "stage": "request_received",
            "truth_note": "Request envelope received by local SymbioSync server; device result not recorded yet.",
            "response_note": "",
            "response_author": "",
            "response_at": "",
        }
        with self._lock:
            idx = self._find_index(request_id)
            if idx is None:
                self._events.append(event)
                self._events = self._events[-self.max_events:]
            else:
                self._events[idx].update(event)
                event = self._events[idx]
            self._write_all()
        return dict(event)

    def record_result(self, request_id: str, result: Any) -> dict | None:
        summary = self._result_summary(result)
        with self._lock:
            idx = self._find_index(request_id)
            if idx is None:
                return None
            event = self._events[idx]
            event.update({
                "result_at": _utc_now(),
                "updated_at": _utc_now(),
                "ok": summary.get("ok"),
                "stage": summary.get("stage", "unknown"),
                "truth_note": summary.get("truth_note", ""),
                "error": summary.get("error", ""),
                "transport": summary.get("transport"),
                "hardware_ack": summary.get("hardware_ack"),
                "observed_effect": summary.get("observed_effect"),
            })
            if "per_device" in summary:
                event["per_device"] = summary["per_device"]
            self._write_all()
            return dict(event)

    def recent(self, limit: int = 100) -> list[dict]:
        with self._lock:
            events = list(self._events[-max(1, min(limit, self.max_events)):])
        return [dict(e) for e in reversed(events)]

    def set_response_note(self, request_id: str, note: str, author: str = "Human") -> dict | None:
        with self._lock:
            idx = self._find_index(request_id)
            if idx is None:
                return None
            event = self._events[idx]
            event["response_note"] = str(note or "")
            event["response_author"] = str(author or "Human")
            event["response_at"] = _utc_now() if note else ""
            event["updated_at"] = _utc_now()
            self._write_all()
            return dict(event)
