from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable

from bridge.artifacts import artifact_items, resolve_local_path
from bridge.task_protocol import read_artifacts, read_status, write_status

Runner = Callable[[list[str]], str]

REQUIRED_CODEX_OUTPUTS = ("plan.json", "artifacts.json")


def build_codex_task_prompt(task_dir: Path) -> str:
    task_path = _display_path(task_dir / "request.md")
    brief_instruction = _brief_instruction(task_dir)
    control_instruction = _control_instruction(task_dir)
    artifact_instruction = _artifact_instruction(task_dir)
    return f"""You are generating local office artifacts for an IM-Collab task.

Read `{task_path}`.
{brief_instruction}
{control_instruction}
{artifact_instruction}

Use Codex + superpowers as the planning and generation method. Do not call Feishu, lark-cli, Presenton, network APIs, or external office tools in this step. Python delivery code will publish the artifacts later.

Do not modify repository source files. Only write inside `{_display_path(task_dir)}`.

Required outputs:
- `plan.json`: object with `task_id` and `steps`; each step has `id`, `title`, and `status`.
- Local artifact files that fit the user's request. Do not force every task into document/slides/whiteboard if the user asked for something else.
- `artifacts.json`: contains `task_id`, `items`, `summary`, and `next_steps`.

Each entry in `items` describes one produced artifact:

```json
{{
  "task_id": "{task_dir.name}",
  "items": [
    {{"id": "brief", "kind": "document", "type": "markdown", "path": "{_display_path(task_dir / 'brief.md')}"}},
    {{"id": "deck", "kind": "slides", "type": "markdown", "path": "{_display_path(task_dir / 'deck.md')}"}}
  ],
  "summary": "...",
  "next_steps": []
}}
```

Use relative or absolute paths in `artifacts.json` that point to the files you created. Preserve the user's requested artifact shape instead of mapping it into fixed fields. Mark the task as complete by writing valid `artifacts.json`; do not publish to Feishu yourself.
"""


def _artifact_instruction(task_dir: Path) -> str:
    artifacts_path = task_dir / "artifacts.json"
    if not artifacts_path.exists():
        return ""
    preview = artifacts_path.read_text(encoding="utf-8").strip()
    return f"""

This task already has delivery metadata in `{_display_path(artifacts_path)}`. If the user asks for modifications, ground the new work in these existing artifacts and update existing Feishu artifacts where possible instead of creating unrelated duplicates.

Current artifacts:

```json
{preview}
```

Update existing Feishu artifacts when the user asks for modifications; do not create unrelated duplicate deliverables unless necessary.
"""


def _brief_instruction(task_dir: Path) -> str:
    brief_json = task_dir / "brief.json"
    brief_md = task_dir / "brief.md"
    if not brief_json.exists() and not brief_md.exists():
        return ""
    return f"""

This task includes a source-grounded group brief:
- `{_display_path(brief_json)}`
- `{_display_path(brief_md)}`

Use `brief.json` as the primary evidence layer for group-chat requirements. Do not add requirements that are not present in the brief or `request.md`. If the brief marks conflicts or open questions, preserve them in generated artifacts and `next_steps` instead of silently resolving them.
"""


def _control_instruction(task_dir: Path) -> str:
    control_log = task_dir / "control.jsonl"
    if not control_log.exists():
        return ""
    preview = control_log.read_text(encoding="utf-8").strip()
    return f"""

This task includes latest operator and group-chat instructions in `{_display_path(control_log)}`. Read them before generating artifacts. These instructions may confirm a previously waiting group brief or add requirements.

Current control log:

```jsonl
{preview}
```
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
        _validate_artifact_item_paths(artifacts, task_dir=task_dir)
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


def _validate_artifact_item_paths(artifacts: dict[str, Any], task_dir: Path | None = None) -> None:
    for item in artifact_items(artifacts):
        resolved = resolve_local_path(item, task_dir=task_dir)
        if resolved is None:
            continue
        if not resolved.exists():
            raise FileNotFoundError(f"missing artifact item file: {resolved}")


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
