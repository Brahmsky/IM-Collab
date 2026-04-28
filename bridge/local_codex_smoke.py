from __future__ import annotations

from pathlib import Path
from typing import Any

from bridge.task_protocol import read_status, write_artifacts, write_status


def run_local_smoke(task_dir: Path) -> dict[str, Any]:
    status = read_status(task_dir)
    task_id = status["task_id"]

    write_status(task_dir, "running")
    request = (task_dir / "request.md").read_text(encoding="utf-8")

    document_path = task_dir / "document.md"
    slides_path = task_dir / "slides.md"
    whiteboard_path = task_dir / "whiteboard.mmd"

    document_path.write_text(_document_markdown(request), encoding="utf-8")
    slides_path.write_text(_slides_markdown(), encoding="utf-8")
    whiteboard_path.write_text(_whiteboard_mermaid(), encoding="utf-8")

    artifacts = {
        "task_id": task_id,
        "document": {"type": "markdown", "path": document_path.as_posix()},
        "slides": {"type": "markdown", "path": slides_path.as_posix()},
        "whiteboard": {"type": "mermaid", "path": whiteboard_path.as_posix()},
        "summary": "Local MVP completed with Codex + superpowers as the orchestration boundary.",
        "next_steps": [
            "Replace the local smoke runner with Codex CLI execution.",
            "Connect Feishu webhook ingress and message egress.",
            "Connect Presenton or a slide-generation gateway.",
        ],
    }
    write_artifacts(task_dir, artifacts)
    write_status(task_dir, "completed")
    return artifacts


def _document_markdown(request: str) -> str:
    return f"""# Agent-Pilot 办公协同系统方案

## 输入摘要

{request.strip()}

## MVP 方案

- IM 入口由 Python Bridge 写入任务目录。
- Codex + superpowers 是唯一主编排层。
- 飞书、Presenton、lark-cli、MCP 和 Gateway 都是外部工具面。
- 任务完成以 `status.json` 和 `artifacts.json` 为准。

## 验收重点

- 覆盖 IM、文档、PPT 或自由画布。
- 展示移动端与桌面端的飞书原生同步。
- 展示 Agent 规划、追问、生成、验收和交付闭环。
"""


def _slides_markdown() -> str:
    return """# 8 页答辩 PPT 大纲

## Slide 1: Agent-Pilot
IM 到办公交付的一键闭环。

## Slide 2: 痛点
团队协作内容分散在聊天、文档、PPT 和白板之间。

## Slide 3: 核心理念
Agent 是主驾驶，GUI 是仪表盘和辅助操作台。

## Slide 4: 总体架构
Feishu IM -> Python Bridge -> Codex + superpowers -> Office tools -> Feishu delivery.

## Slide 5: 文件协议
request.md、status.json、artifacts.json 构成稳定边界。

## Slide 6: 工具层
lark-cli、lark-openapi-mcp、Presenton 和 Gateway 都作为 Codex 可调用工具。

## Slide 7: 演示路径
群聊触发、方案生成、PPT 生成、白板流程图、交付回传。

## Slide 8: 价值
把跨应用搬运变成面向目标的 Agent 编排。
"""


def _whiteboard_mermaid() -> str:
    return """flowchart TD
    A[Feishu IM request] --> B[Python Bridge]
    B --> C[Task directory]
    C --> D[Codex + superpowers]
    D --> E[Feishu docs]
    D --> F[Presenton slides]
    D --> G[Whiteboard flow]
    E --> H[artifacts.json]
    F --> H
    G --> H
    H --> I[Feishu delivery message]
"""
