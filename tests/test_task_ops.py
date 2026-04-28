from __future__ import annotations

from pathlib import Path

from bridge.task_ops import ack_task, parse_golembot_request, retry_golembot_task


def test_ack_task_writes_operator_ack_metadata(tmp_path: Path) -> None:
    task_dir = tmp_path / "task-1"

    ack = ack_task(task_dir, operator="li", note="已确认错误，稍后重试")

    assert ack["operator"] == "li"
    assert ack["note"] == "已确认错误，稍后重试"
    assert (task_dir / "ack.json").exists()


def test_parse_golembot_request_reads_session_fields_and_message(tmp_path: Path) -> None:
    task_dir = tmp_path / "task-1"
    task_dir.mkdir()
    (task_dir / "request.md").write_text(
        """# GolemBot Office Request

session_key: feishu:oc_group
chat_id: oc_group
sender_id: ou_user

## User Message

生成项目方案和 PPT

## Execution Boundary

tools
""",
        encoding="utf-8",
    )

    request = parse_golembot_request(task_dir)

    assert request == {
        "session_key": "feishu:oc_group",
        "chat_id": "oc_group",
        "sender_id": "ou_user",
        "message": "生成项目方案和 PPT",
    }


def test_retry_golembot_task_reuses_existing_task_protocol(tmp_path: Path) -> None:
    task_dir = tmp_path / "task-1"
    task_dir.mkdir()
    (task_dir / "request.md").write_text(
        """# GolemBot Office Request

session_key: feishu:oc_group
chat_id: oc_group
sender_id: ou_user

## User Message

生成项目方案和 PPT

## Execution Boundary

tools
""",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return {"task_id": "task-1", "task_dir": task_dir.as_posix()}

    result = retry_golembot_task(task_dir, generator="app-server", publish=True, runner=fake_runner)

    assert result["task_id"] == "task-1"
    assert seen["message"] == "生成项目方案和 PPT"
    assert seen["session_key"] == "feishu:oc_group"
    assert seen["chat_id"] == "oc_group"
    assert seen["sender_id"] == "ou_user"
    assert seen["tasks_root"] == tmp_path
    assert seen["task_id"] == "task-1"
    assert seen["generator"] == "app-server"
    assert seen["publish"] is True
