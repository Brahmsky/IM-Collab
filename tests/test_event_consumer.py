from __future__ import annotations

import json
from pathlib import Path

from bridge.event_consumer import EventConsumer, EventConsumerConfig


def write_event(path: Path, message_id: str, content: str = "生成项目方案") -> None:
    path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": message_id,
                "chat_id": "oc_123",
                "chat_type": "p2p",
                "message_type": "text",
                "content": content,
                "sender_id": "ou_user",
                "timestamp": "1777305792858",
            }
        ),
        encoding="utf-8",
    )


def test_consumer_processes_new_event_once(tmp_path: Path) -> None:
    event_dir = tmp_path / "events"
    event_dir.mkdir()
    event_file = event_dir / "im.message.receive_v1_a.json"
    write_event(event_file, "om_123")
    processed: list[Path] = []

    consumer = EventConsumer(
        EventConsumerConfig(event_dir=event_dir, tasks_root=tmp_path / "tasks", state_path=tmp_path / "state.json"),
        handler=lambda path: processed.append(path),
    )

    first = consumer.process_once()
    second = consumer.process_once()

    assert first == 1
    assert second == 0
    assert processed == [event_file]
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["processed_message_ids"] == ["om_123"]


def test_consumer_skips_bot_self_messages(tmp_path: Path) -> None:
    event_dir = tmp_path / "events"
    event_dir.mkdir()
    event_file = event_dir / "im.message.receive_v1_a.json"
    write_event(event_file, "om_123")
    payload = json.loads(event_file.read_text(encoding="utf-8"))
    payload["sender_id"] = "ou_bot"
    event_file.write_text(json.dumps(payload), encoding="utf-8")
    processed: list[Path] = []

    consumer = EventConsumer(
        EventConsumerConfig(
            event_dir=event_dir,
            tasks_root=tmp_path / "tasks",
            state_path=tmp_path / "state.json",
            bot_open_ids=frozenset({"ou_bot"}),
        ),
        handler=lambda path: processed.append(path),
    )

    assert consumer.process_once() == 0
    assert processed == []
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["skipped_message_ids"] == ["om_123"]


def test_consumer_moves_failed_events_to_failed_dir(tmp_path: Path) -> None:
    event_dir = tmp_path / "events"
    event_dir.mkdir()
    event_file = event_dir / "im.message.receive_v1_a.json"
    write_event(event_file, "om_123")

    def fail_handler(path: Path) -> None:
        raise RuntimeError("boom")

    consumer = EventConsumer(
        EventConsumerConfig(event_dir=event_dir, tasks_root=tmp_path / "tasks", state_path=tmp_path / "state.json"),
        handler=fail_handler,
    )

    assert consumer.process_once() == 0
    failed_file = tmp_path / "events" / "failed" / event_file.name
    assert failed_file.exists()
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["failed_message_ids"] == ["om_123"]
