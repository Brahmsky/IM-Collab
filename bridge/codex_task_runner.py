from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable

from bridge.task_protocol import read_artifacts, read_status, write_status

Runner = Callable[[list[str]], str]

REQUIRED_CODEX_OUTPUTS = ("plan.json", "document.md", "slides.md", "whiteboard.mmd", "artifacts.json")


def build_codex_task_prompt(task_dir: Path) -> str:
    task_path = _display_path(task_dir / "request.md")
    return f"""You are generating local office artifacts for an IM-Collab task.

Read `{task_path}`.

Use Codex + superpowers as the planning and generation method. Do not call Feishu, lark-cli, Presenton, network APIs, or external office tools in this step. Python delivery code will publish the artifacts later.

Do not modify repository source files. Only write inside `{_display_path(task_dir)}`.

Required outputs:
- `plan.json`: object with `task_id` and `steps`; each step has `id`, `title`, and `status`.
- `document.md`: project方案 document in Markdown.
- `slides.md`: 6-10 slide outline in Markdown, using `## Slide N: Title` headings.
- `whiteboard.mmd`: Mermaid flowchart.
- `artifacts.json`: must contain `task_id`, `document`, `slides`, `whiteboard`, `summary`, and `next_steps`.

`document`, `slides`, and `whiteboard` in `artifacts.json` MUST be objects, not strings:

```json
{{
  "task_id": "{task_dir.name}",
  "document": {{"type": "markdown", "path": "{_display_path(task_dir / 'document.md')}"}},
  "slides": {{"type": "markdown", "path": "{_display_path(task_dir / 'slides.md')}"}},
  "whiteboard": {{"type": "mermaid", "path": "{_display_path(task_dir / 'whiteboard.mmd')}"}},
  "summary": "...",
  "next_steps": []
}}
```

Use relative or absolute paths in `artifacts.json` that point to the files you created. Mark the task as complete by writing valid `artifacts.json`; do not publish to Feishu yourself.
"""


def build_codex_task_args(
    task_dir: Path,
    project_root: Path,
    codex_cmd: tuple[str, ...] = ("codex", "exec"),
) -> list[str]:
    return [
        *codex_cmd,
        "--cd",
        project_root.as_posix(),
        "--sandbox",
        "workspace-write",
        "--add-dir",
        task_dir.as_posix(),
        build_codex_task_prompt(task_dir),
    ]


def run_codex_task(
    task_dir: Path,
    project_root: Path | None = None,
    runner: Runner | None = None,
) -> dict[str, Any]:
    read_status(task_dir)
    write_status(task_dir, "running")
    project_root = project_root or Path.cwd()
    args = build_codex_task_args(task_dir, project_root=project_root)

    try:
        if runner:
            runner(args)
        else:
            _subprocess_runner(args)
        _validate_codex_outputs(task_dir)
        artifacts = read_artifacts(task_dir)
    except Exception as exc:
        write_status(task_dir, "failed", error=f"missing Codex output or invalid artifact contract: {exc}")
        raise

    write_status(task_dir, "completed")
    return artifacts


def _validate_codex_outputs(task_dir: Path) -> None:
    for filename in REQUIRED_CODEX_OUTPUTS:
        path = task_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"missing Codex output: {path}")


def _subprocess_runner(args: list[str]) -> str:
    completed = subprocess.run(args, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"codex exec failed with code {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()
