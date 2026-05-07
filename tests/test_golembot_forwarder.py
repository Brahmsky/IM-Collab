from __future__ import annotations

from bridge.golembot_forwarder import build_golembot_prompt, forward_event_to_golembot


def test_build_golembot_prompt_includes_event_metadata() -> None:
    event = {
        "type": "im.message.receive_v1",
        "message_id": "om_123",
        "chat_id": "oc_456",
        "chat_type": "p2p",
        "message_type": "text",
        "content": "生成项目方案",
        "sender_id": "ou_789",
    }

    prompt = build_golembot_prompt(event)

    assert "生成项目方案" in prompt
    assert "message_id: om_123" in prompt
    assert "session_key: feishu:oc_456:ou_789" in prompt
    assert "cd /home/lifei/Programs/IM-Collab" in prompt
    assert "scripts/run_golembot_office_task.py" in prompt
    assert "--task-id im-om_123" in prompt
    assert "--generator app-server" in prompt
    assert "--generator local" not in prompt


def test_build_golembot_prompt_keeps_publish_outside_codex() -> None:
    event = {
        "type": "im.message.receive_v1",
        "message_id": "om_123",
        "chat_id": "oc_456",
        "chat_type": "p2p",
        "message_type": "text",
        "content": "生成项目方案",
        "sender_id": "ou_789",
    }

    prompt = build_golembot_prompt(event, publish=True)

    assert "--publish" not in prompt
    assert "directly create or update the requested Feishu-native artifacts" in prompt
    assert "local task artifacts" not in prompt


def test_forward_event_to_golembot_posts_chat_request_with_codex_generator() -> None:
    event = {
        "type": "im.message.receive_v1",
        "message_id": "om_123",
        "chat_id": "oc_456",
        "chat_type": "group",
        "message_type": "text",
        "content": "生成项目方案",
        "sender_id": "ou_789",
    }
    seen: dict[str, object] = {}

    def fake_transport(url: str, token: str, payload: dict[str, str]) -> dict[str, object]:
        seen["url"] = url
        seen["token"] = token
        seen["payload"] = payload
        return {"ok": True, "finalText": "任务完成"}

    result = forward_event_to_golembot(
        event,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        generator="codex",
        transport=fake_transport,
    )

    assert seen["url"] == "http://127.0.0.1:3199/chat"
    assert seen["token"] == "secret"
    assert seen["payload"]["sessionKey"] == "feishu:oc_456"
    assert "生成项目方案" in seen["payload"]["message"]
    assert "--generator codex" in seen["payload"]["message"]
    assert result["response"]["finalText"] == "任务完成"
