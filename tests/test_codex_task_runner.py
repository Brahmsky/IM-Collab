from __future__ import annotations

import json
from pathlib import Path

from bridge.codex_task_runner import (
    _validate_artifact_item_paths,
    build_codex_task_args,
    build_codex_task_prompt,
    run_codex_task,
)
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
    assert "items" in prompt
    assert "不要因为实现方便，就强行把所有任务都产出成 `document/slides/whiteboard`" in prompt
    assert "这一步不要调用飞书" in prompt
    assert "不要修改仓库里的源代码文件" in prompt


def test_build_codex_task_prompt_prefers_group_brief_when_present(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Generate a deck.")
    (task_dir / "brief.json").write_text('{"annotations":[]}\n', encoding="utf-8")
    (task_dir / "brief.md").write_text("# brief\n", encoding="utf-8")

    prompt = build_codex_task_prompt(task_dir)

    assert "brief.json" in prompt
    assert "brief.md" in prompt
    assert "有来源依据的群聊 brief" in prompt


def test_build_codex_task_prompt_includes_control_log_when_present(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Generate a deck.")
    (task_dir / "control.jsonl").write_text(
        '{"type":"append_instruction","payload":{"text":"确认按 8 页 PPT 执行"}}\n',
        encoding="utf-8",
    )

    prompt = build_codex_task_prompt(task_dir)

    assert "control.jsonl" in prompt
    assert "append_instruction" in prompt
    assert "最新的操作员补充和群聊指令" in prompt


def test_build_codex_task_prompt_includes_existing_artifacts_for_followup(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "把刚才的 PPT 改成 5 分钟答辩版。")
    (task_dir / "artifacts.json").write_text(
        json.dumps(
            {
                "task_id": "im-om_123",
                "slides": {"remote": {"url": "https://feishu/slides"}},
                "summary": "已发布初版。",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    prompt = build_codex_task_prompt(task_dir)

    assert "artifacts.json" in prompt
    assert "https://feishu/slides" in prompt
    assert "优先基于这些现有工件继续修改" in prompt


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
    assert args[-1].startswith("你正在为 IM-Collab 任务生成本地办公产物。")


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


def test_validate_artifact_item_paths_accepts_repo_relative_task_path(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "task-1", "Reply ok.")
    (task_dir / "reply.md").write_text("ok\n", encoding="utf-8")
    artifacts = {
        "task_id": "task-1",
        "items": [{"id": "reply", "kind": "message", "path": "tasks/task-1/reply.md"}],
    }

    _validate_artifact_item_paths(artifacts, task_dir=task_dir)


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
