from __future__ import annotations

from pathlib import Path

from bridge.task_binding import (
    bind_active_task,
    build_golembot_session_key,
    clear_active_task,
    get_task_binding,
)


def test_build_golembot_session_key_matches_feishu_group_conversation() -> None:
    assert (
        build_golembot_session_key(
            channel_type="feishu",
            chat_id="oc_123",
            sender_id="ou_456",
            chat_type="group",
        )
        == "feishu:oc_123"
    )


def test_build_golembot_session_key_can_isolate_group_sessions() -> None:
    assert (
        build_golembot_session_key(
            channel_type="feishu",
            chat_id="oc_123",
            sender_id="ou_456",
            chat_type="group",
            thread_id="om_new",
        )
        == "feishu:oc_123:session:om_new"
    )


def test_build_golembot_session_key_matches_feishu_dm_session() -> None:
    assert (
        build_golembot_session_key(
            channel_type="feishu",
            chat_id="oc_123",
            sender_id="ou_456",
            chat_type="p2p",
        )
        == "feishu:oc_123:ou_456"
    )


def test_bind_active_task_creates_durable_task_binding(tmp_path: Path) -> None:
    index_path = tmp_path / "task-bindings.json"

    entry = bind_active_task(
        index_path,
        session_key="feishu:oc_123",
        task_id="im-om_123",
        chat_id="oc_123",
        channel_type="feishu",
        sender_id="ou_456",
        codex_thread_id="thread_abc",
        active_turn_id="turn_123",
    )

    assert entry["active_task_id"] == "im-om_123"
    assert entry["codex_thread_id"] == "thread_abc"
    assert entry["active_turn_id"] == "turn_123"
    assert get_task_binding(index_path, "feishu:oc_123")["chat_id"] == "oc_123"


def test_bind_active_task_can_store_last_absorbed_message_id(tmp_path: Path) -> None:
    index_path = tmp_path / "task-bindings.json"

    entry = bind_active_task(
        index_path,
        session_key="feishu:oc_group:session:om_new",
        task_id="im-om_new",
        chat_id="oc_group",
        channel_type="feishu",
        sender_id="ou_456",
        last_absorbed_message_id="om_trigger",
    )

    assert entry["last_absorbed_message_id"] == "om_trigger"
    assert get_task_binding(index_path, "feishu:oc_group:session:om_new")["last_absorbed_message_id"] == "om_trigger"


def test_bind_active_task_can_store_chat_name(tmp_path: Path) -> None:
    index_path = tmp_path / "task-bindings.json"

    entry = bind_active_task(
        index_path,
        session_key="feishu:oc_group",
        task_id="im-om_123",
        chat_id="oc_group",
        channel_type="feishu",
        sender_id="ou_456",
        chat_name="IM-Collab 群聊测试",
    )

    assert entry["chat_name"] == "IM-Collab 群聊测试"
    assert get_task_binding(index_path, "feishu:oc_group")["chat_name"] == "IM-Collab 群聊测试"


def test_clear_active_task_preserves_last_task(tmp_path: Path) -> None:
    index_path = tmp_path / "task-bindings.json"
    bind_active_task(
        index_path,
        session_key="feishu:oc_123",
        task_id="im-om_123",
        chat_id="oc_123",
        channel_type="feishu",
        sender_id="ou_456",
    )

    entry = clear_active_task(index_path, "feishu:oc_123")

    assert entry["active_task_id"] is None
    assert entry["last_task_id"] == "im-om_123"
    assert get_task_binding(index_path, "feishu:oc_123")["last_task_id"] == "im-om_123"
