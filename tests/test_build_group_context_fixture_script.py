from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_group_context_fixture_script_writes_normalized_messages(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "events"
    fixture_dir.mkdir()
    output_path = tmp_path / "normalized" / "messages.json"
    (fixture_dir / "001.json").write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_notice",
                "chat_id": "oc_product",
                "chat_type": "group",
                "message_type": "text",
                "sender_id": "ou_pm",
                "timestamp": "1777395600000",
                "content": "正式通知：周五 18:00 前提交复盘文档。",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_group_context_fixture.py",
            "--input",
            str(fixture_dir),
            "--output",
            str(output_path),
            "--chat-id",
            "oc_product",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert "messages=1" in result.stdout
    messages = json.loads(output_path.read_text(encoding="utf-8"))
    assert messages[0]["message_id"] == "om_notice"
    assert messages[0]["content"] == "正式通知：周五 18:00 前提交复盘文档。"
