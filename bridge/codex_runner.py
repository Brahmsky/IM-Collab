from __future__ import annotations

from pathlib import Path
from typing import Sequence


def build_codex_prompt(task_dir: Path) -> str:
    task_path = _display_path(task_dir / "request.md")
    artifacts_path = _display_path(task_dir / "artifacts.json")
    status_path = _display_path(task_dir / "status.json")
    return f"""You are executing an IM-Collab task.

Read `{task_path}` and use Codex + superpowers as the only orchestration layer.

Use existing office wheels first:
- Feishu CLI built-in AI Agent Skills for IM, docs, drive, and whiteboard-oriented document operations.
- lark-openapi-mcp when broader Feishu/Lark OpenAPI coverage is needed.
- Presenton API or MCP for PPTX/PDF generation.

Do not use OMO or OMX. Do not implement office-suite behavior from scratch when an existing tool can do it.

Write progress to `{status_path}` and final delivery metadata to `{artifacts_path}`. Completion is valid only when `artifacts.json` contains document, slides, whiteboard, summary, and next_steps.
"""


def build_codex_subprocess_args(task_dir: Path, codex_cmd: Sequence[str] = ("codex",)) -> list[str]:
    return [*codex_cmd, build_codex_prompt(task_dir)]


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()
