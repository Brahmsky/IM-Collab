from __future__ import annotations

import json
from pathlib import Path

from bridge.codex_task_runner import build_codex_task_args, build_codex_task_prompt, run_codex_task
from bridge.task_protocol import create_task, read_artifacts, read_status


def write_codex_outputs(task_dir: Path) -> None:
    (task_dir / "plan.json").write_text(
        json.dumps(
            {
                "task_id": task_dir.name,
                "steps": [
                    {"id": "understand", "title": "Understand request", "status": "completed"},
                    {"id": "draft", "title": "Draft office artifacts", "status": "completed"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (task_dir / "document.md").write_text("# Agent plan\n", encoding="utf-8")
    (task_dir / "slides.md").write_text("# Deck\n\n## Slide 1: Cover\nIntro\n", encoding="utf-8")
    (task_dir / "whiteboard.mmd").write_text("flowchart TD\nA-->B\n", encoding="utf-8")
    (task_dir / "artifacts.json").write_text(
        json.dumps(
            {
                "task_id": task_dir.name,
                "document": {"type": "markdown", "path": (task_dir / "document.md").as_posix()},
                "slides": {"type": "markdown", "path": (task_dir / "slides.md").as_posix()},
                "whiteboard": {"type": "mermaid", "path": (task_dir / "whiteboard.mmd").as_posix()},
                "summary": "Codex generated office artifacts.",
                "next_steps": ["Publish to Feishu."],
            }
        ),
        encoding="utf-8",
    )


def test_build_codex_task_prompt_is_file_protocol_only(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Generate a deck.")

    prompt = build_codex_task_prompt(task_dir)

    assert "request.md" in prompt
    assert "plan.json" in prompt
    assert "document.md" in prompt
    assert "slides.md" in prompt
    assert "whiteboard.mmd" in prompt
    assert "Do not call Feishu" in prompt
    assert "Do not modify repository source files" in prompt


def test_build_codex_task_args_uses_codex_exec_with_workspace_write(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Generate a deck.")

    args = build_codex_task_args(task_dir, project_root=Path("/repo"))

    assert args[:2] == ["codex", "exec"]
    assert "--cd" in args
    assert "/repo" in args
    assert "--sandbox" in args
    assert "workspace-write" in args
    assert "--ask-for-approval" not in args
    assert "--add-dir" in args
    assert task_dir.as_posix() in args
    assert args[-1].startswith("You are generating local office artifacts")


def test_run_codex_task_validates_outputs_and_marks_completed(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Generate a deck.")
    seen_args: list[str] = []

    def fake_runner(args: list[str]) -> str:
        seen_args.extend(args)
        write_codex_outputs(task_dir)
        return "codex done"

    artifacts = run_codex_task(task_dir, project_root=tmp_path, runner=fake_runner)

    assert seen_args[:2] == ["codex", "exec"]
    assert read_status(task_dir)["state"] == "completed"
    assert artifacts == read_artifacts(task_dir)
    assert artifacts["summary"] == "Codex generated office artifacts."


def test_run_codex_task_marks_failed_when_outputs_missing(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Generate a deck.")

    def fake_runner(args: list[str]) -> str:
        return "no files"

    try:
        run_codex_task(task_dir, project_root=tmp_path, runner=fake_runner)
    except FileNotFoundError:
        pass

    status = read_status(task_dir)
    assert status["state"] == "failed"
    assert "missing Codex output" in status["error"]
