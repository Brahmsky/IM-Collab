from __future__ import annotations

from pathlib import Path

from bridge.codex_runner import build_codex_prompt, build_codex_subprocess_args
from bridge.task_protocol import create_task


def test_build_codex_prompt_routes_office_work_to_existing_wheels(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "demo-task", "Create Feishu docs and slides.")

    prompt = build_codex_prompt(task_dir)

    assert "demo-task/request.md" in prompt
    assert "Codex + superpowers" in prompt
    assert "Feishu CLI built-in AI Agent Skills" in prompt
    assert "lark-openapi-mcp" in prompt
    assert "Presenton" in prompt
    assert "artifacts.json" in prompt
    assert "Do not use OMO or OMX" in prompt


def test_build_codex_subprocess_args_uses_configurable_command(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "demo-task", "Create Feishu docs and slides.")

    args = build_codex_subprocess_args(task_dir, codex_cmd=("codex", "exec"))

    assert args[0:2] == ["codex", "exec"]
    assert args[-1].startswith("You are executing an IM-Collab task.")
    assert "demo-task/request.md" in args[-1]
