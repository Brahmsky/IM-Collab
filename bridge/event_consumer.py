from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from bridge.feishu_events import is_card_action_event, parse_card_action_event, parse_im_event

Handler = Callable[[Path], None]


@dataclass(frozen=True)
class EventConsumerConfig:
    event_dir: Path
    tasks_root: Path
    state_path: Path
    bot_open_ids: frozenset[str] = field(default_factory=frozenset)
    glob_pattern: str = "*.json"
    poll_interval_seconds: float = 1.0


class EventConsumer:
    def __init__(self, config: EventConsumerConfig, handler: Handler) -> None:
        self.config = config
        self.handler = handler

    def process_once(self) -> int:
        self.config.event_dir.mkdir(parents=True, exist_ok=True)
        state = self._load_state()
        processed_count = 0

        for event_path in sorted(self.config.event_dir.glob(self.config.glob_pattern)):
            payload = _read_json(event_path)
            event_id, sender_open_id = _event_identity(payload)
            if event_id in state["processed_message_ids"]:
                continue
            if event_id in state["failed_message_ids"]:
                continue
            if sender_open_id in self.config.bot_open_ids:
                _append_unique(state, "skipped_message_ids", event_id)
                _append_unique(state, "processed_message_ids", event_id)
                self._save_state(state)
                continue

            try:
                self.handler(event_path)
            except Exception:
                _append_unique(state, "failed_message_ids", event_id)
                self._move_failed(event_path)
                self._save_state(state)
                continue

            _append_unique(state, "processed_message_ids", event_id)
            self._save_state(state)
            processed_count += 1

        return processed_count

    def run_forever(self) -> None:
        while True:
            self.process_once()
            time.sleep(self.config.poll_interval_seconds)

    def _load_state(self) -> dict[str, list[str]]:
        if not self.config.state_path.exists():
            return {"processed_message_ids": [], "skipped_message_ids": [], "failed_message_ids": []}
        data = _read_json(self.config.state_path)
        return {
            "processed_message_ids": list(data.get("processed_message_ids", [])),
            "skipped_message_ids": list(data.get("skipped_message_ids", [])),
            "failed_message_ids": list(data.get("failed_message_ids", [])),
        }

    def _save_state(self, state: dict[str, list[str]]) -> None:
        self.config.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _move_failed(self, event_path: Path) -> None:
        failed_dir = self.config.event_dir / "failed"
        failed_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(event_path.as_posix(), (failed_dir / event_path.name).as_posix())


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"event json root must be an object: {path}")
    return data


def _event_identity(payload: dict[str, Any]) -> tuple[str, str]:
    if is_card_action_event(payload):
        parsed = parse_card_action_event(payload)
        return parsed.message_id or json.dumps(parsed.value, sort_keys=True, ensure_ascii=False), parsed.sender_open_id
    parsed = parse_im_event(payload)
    return parsed.message_id, parsed.sender_open_id


def _append_unique(state: dict[str, list[str]], key: str, value: str) -> None:
    if value not in state[key]:
        state[key].append(value)
