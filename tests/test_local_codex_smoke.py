from __future__ import annotations

from pathlib import Path

from bridge.local_codex_smoke import run_local_smoke
from bridge.task_protocol import create_task, read_artifacts, read_status


def test_run_local_smoke_writes_completed_office_artifacts(tmp_path: Path) -> None:
    task_dir = create_task(
        root=tmp_path,
        task_id="demo-local-smoke",
        request_markdown=(
            "# IM Context\n\n"
            "团队正在讨论 Agent-Pilot 办公协同系统。\n\n"
            "# User Request\n\n"
            "根据群聊生成项目方案、8 页答辩 PPT 和白板流程图。"
        ),
    )

    artifacts = run_local_smoke(task_dir)

    status = read_status(task_dir)
    assert status["state"] == "completed"
    assert status["error"] is None
    assert artifacts == read_artifacts(task_dir)
    assert artifacts["task_id"] == "demo-local-smoke"
    paths = {item["kind"]: item["path"] for item in artifacts["items"]}
    assert paths["document"].endswith("document.md")
    assert paths["slides"].endswith("slides.md")
    assert paths["whiteboard"].endswith("whiteboard.mmd")
    assert "Codex + superpowers" in artifacts["summary"]
    assert artifacts["next_steps"] == [
        "Replace the local smoke runner with Codex CLI execution.",
        "Connect Feishu webhook ingress and message egress.",
        "Connect Presenton or a slide-generation gateway.",
    ]

    assert (task_dir / "document.md").read_text(encoding="utf-8").startswith("# Agent-Pilot")
    assert "Slide 1" in (task_dir / "slides.md").read_text(encoding="utf-8")
    assert "flowchart TD" in (task_dir / "whiteboard.mmd").read_text(encoding="utf-8")
