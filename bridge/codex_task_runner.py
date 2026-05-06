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
    return f"""你正在为 IM-Collab 任务生成本地办公产物。

请先阅读 `{task_path}`。
{brief_instruction}
{control_instruction}
{artifact_instruction}

请使用 Codex 和 superpowers 进行规划和生成。这一步不要调用飞书、`lark-cli`、Presenton、网络 API 或其他外部办公工具；后续会由 Python 交付代码负责发布产物。

不要修改仓库里的源代码文件。你只能在 `{_display_path(task_dir)}` 目录内写入文件。

你必须产出：
- `plan.json`：一个包含 `task_id` 和 `steps` 的对象；每个 step 必须带有 `id`、`title` 和 `status`。
- 符合用户请求的本地工件文件。不要因为实现方便，就强行把所有任务都产出成 `document/slides/whiteboard`；如果用户要的是别的内容，就按真实需求产出。
- `artifacts.json`：必须包含 `task_id`、`items`、`summary` 和 `next_steps`。

`items` 里的每一项都描述一个你生成出来的工件，例如：

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

`artifacts.json` 里的路径可以是相对路径，也可以是绝对路径，但都必须真实指向你刚生成的文件。请保留用户实际需要的工件结构，不要为了适配固定字段而改写需求。任务完成的标志是写出合法的 `artifacts.json`；不要在这一步自行发布到飞书。
"""


def _artifact_instruction(task_dir: Path) -> str:
    artifacts_path = task_dir / "artifacts.json"
    if not artifacts_path.exists():
        return ""
    preview = artifacts_path.read_text(encoding="utf-8").strip()
    return f"""

这个任务已经在 `{_display_path(artifacts_path)}` 里有一份交付元数据。如果用户是在继续修改上一轮结果，你要优先基于这些现有工件继续修改，并尽量更新已有的飞书工件，而不是无关地再造一份重复交付。

当前工件如下：

```json
{preview}
```

当用户要求修改时，优先更新已有飞书工件；除非确实必要，否则不要创建无关的重复交付物。
"""


def _brief_instruction(task_dir: Path) -> str:
    brief_json = task_dir / "brief.json"
    brief_md = task_dir / "brief.md"
    if not brief_json.exists() and not brief_md.exists():
        return ""
    return f"""

这个任务附带了一份有来源依据的群聊 brief：
- `{_display_path(brief_json)}`
- `{_display_path(brief_md)}`

请把 `brief.json` 当作群聊需求的主证据层。不要添加 `brief` 或 `request.md` 里没有出现过的要求。如果 brief 标出了冲突或待确认项，请在生成的工件和 `next_steps` 里保留这些信息，不要擅自替用户消解。
"""


def _control_instruction(task_dir: Path) -> str:
    control_log = task_dir / "control.jsonl"
    if not control_log.exists():
        return ""
    preview = control_log.read_text(encoding="utf-8").strip()
    return f"""

这个任务在 `{_display_path(control_log)}` 里记录了最新的操作员补充和群聊指令。生成工件前先读它们。这些指令可能是在确认之前待处理的 brief，也可能是在补充新需求。

当前控制日志：

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
