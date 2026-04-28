from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_forward_script_can_dry_run(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_123",
                "chat_id": "oc_456",
                "chat_type": "p2p",
                "message_type": "text",
                "content": "生成项目方案",
                "sender_id": "ou_789",
            }
        ),
        encoding="utf-8",
    )
    script = Path(__file__).resolve().parents[1] / "scripts" / "forward_feishu_event_to_golembot.py"

    completed = subprocess.run(
        [sys.executable, script.as_posix(), event_path.as_posix(), "--dry-run"],
        check=True,
        text=True,
        capture_output=True,
    )

    result = json.loads(completed.stdout)
    assert result["session_key"] == "feishu:oc_456:ou_789"
    assert "scripts/run_golembot_office_task.py" in result["message"]
    assert "--generator app-server" in result["message"]


def test_forward_script_can_dry_run_reply_from_response_file(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_123",
                "chat_id": "oc_456",
                "chat_type": "p2p",
                "message_type": "text",
                "content": "生成项目方案",
                "sender_id": "ou_789",
            }
        ),
        encoding="utf-8",
    )
    response_path = tmp_path / "golembot-response.json"
    response_path.write_text(
        json.dumps({"response": {"finalText": "日志。任务 `gb-123` 已完成。\n\n**文档**: doc"}}),
        encoding="utf-8",
    )
    script = Path(__file__).resolve().parents[1] / "scripts" / "forward_feishu_event_to_golembot.py"

    completed = subprocess.run(
        [
            sys.executable,
            script.as_posix(),
            event_path.as_posix(),
            "--reply-from-response",
            response_path.as_posix(),
            "--dry-run-reply",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    result = json.loads(completed.stdout)
    assert result["reply_markdown"].startswith("任务 `gb-123` 已完成")
    assert result["reply"]["dry_run"] is True
