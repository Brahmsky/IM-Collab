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
    return f"""你正在执行一个 IM-Collab 办公任务。

请先阅读 `{task_path}`。
{brief_instruction}
{control_instruction}
{artifact_instruction}

请使用 Codex 和 superpowers 进行规划和执行。你可以根据任务需要调用当前环境里可用的工具、CLI、服务或外部能力，包括飞书相关能力、`lark-cli`、Presenton、网络 API 等；不要为了遵守某个预设模板而放弃更直接、更可靠的执行路径。

核心边界只有两条：
- 不要修改仓库里的业务源代码文件，除非用户明确要求你改仓库代码本身。
- 无论你中间调用了什么工具，最终都要把本任务的可追踪结果落到 `{_display_path(task_dir)}` 内，并按协议写好状态和交付元数据。

你必须产出：
- `plan.json`：一个包含 `task_id` 和 `steps` 的对象；每个 step 必须带有 `id`、`title` 和 `status`。
- 符合用户请求的工件文件或结果记录。不要因为实现方便，就强行把所有任务都产出成 `document/slides/whiteboard`；如果用户要的是别的内容，就按真实需求交付。
- `artifacts.json`：必须包含 `task_id`、`items`、`summary` 和 `next_steps`，并把每个工件写成稳定 schema，而不是临时拼字段。

`items` 里的每一项都描述一个你生成出来的工件，例如：

```json
{{
  "task_id": "{task_dir.name}",
  "items": [
    {{
      "id": "proposal",
      "kind": "document",
      "family": "document",
      "input": {{"format": "docx_xml", "path": "{_display_path(task_dir / 'proposal.xml')}"}},
      "output": {{
        "provider": "feishu",
        "object_type": "document",
        "document_id": "doc_xxx",
        "url": "https://example.feishu.cn/docx/doc_xxx"
      }},
      "display": {{
        "card_kind": "document",
        "label": "项目方案",
        "click_url": "https://example.feishu.cn/docx/doc_xxx",
        "preview_value": "https://example.feishu.cn/docx/doc_xxx",
        "clickable": true
      }},
      "delivery": {{"feishu_card_mode": "link_button"}}
    }},
    {{
      "id": "deck",
      "kind": "slides",
      "family": "slides",
      "input": {{"format": "slides_xml", "path": "{_display_path(task_dir / 'deck.slides.json')}"}},
      "output": {{
        "provider": "feishu",
        "object_type": "slides",
        "xml_presentation_id": "slides_xxx",
        "url": "https://example.feishu.cn/slides/slides_xxx"
      }},
      "display": {{
        "card_kind": "slides",
        "label": "答辩 PPT",
        "click_url": "https://example.feishu.cn/slides/slides_xxx",
        "preview_value": "https://example.feishu.cn/slides/slides_xxx",
        "clickable": true
      }},
      "delivery": {{"feishu_card_mode": "link_button"}}
    }}
  ],
  "summary": "...",
  "next_steps": []
}}
```

请直接调用 `lark-cli`、Feishu OpenAPI 和现有 office wheels 去创建或更新真实飞书对象，而不是退回“先写本地 markdown，再让 Python 二次转换”的低能力路径。

`artifacts.json` 里的路径可以是相对路径，也可以是绝对路径，但都必须真实指向你生成、下载、整理或更新后的结果文件。请保留用户实际需要的工件结构，不要为了适配固定字段而改写需求。

如果你直接生成了飞书文档、飞书演示文稿、飞书画板或其他远端结果，也要把相关本地说明文件、导出文件、链接信息或远端元数据以 `items` 的形式写入 `artifacts.json`，保证后续链路能继续消费。

任务完成的标志是写出合法的 `artifacts.json`。不要把“是否用了外部工具”当成限制，重点是结果真实可追踪、协议完整、交付符合要求。
"""


def _artifact_instruction(task_dir: Path) -> str:
    artifacts_path = task_dir / "artifacts.json"
    if not artifacts_path.exists():
        return ""
    preview = artifacts_path.read_text(encoding="utf-8").strip()
    return f"""

这个任务已经在 `{_display_path(artifacts_path)}` 里有一份交付元数据。如果用户是在继续修改上一轮结果，你要优先基于这些现有工件继续修改，并尽量复用、更新或衔接已有的飞书工件，而不是无关地再造一份重复交付。

当前工件如下：

```json
{preview}
```

当用户要求修改时，优先更新已有工件链路；除非确实必要，否则不要创建无关的重复交付物。
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
