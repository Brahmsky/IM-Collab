# Codex-Direct Feishu Execution Design

## Goal

把 IM-Collab 从“Codex 先产出本地 Markdown/Mermaid，再由 Python bridge 二次发布飞书文档 / Slides / 白板”的旧链路，重构成“Codex 直接调用 office wheels 产出真实飞书对象，任务目录只承担协议与审计”的主链路。

## Context

当前仓库已经具备三类真实远端能力：

- 文档：`bridge/lark_docs.py`
- Slides：`bridge/lark_slides.py`
- 白板：`bridge/lark_whiteboard.py`

但默认执行路径仍被以下旧设计锁住：

- `bridge/golembot_office_loop.py` 默认 `generator="local"`
- `bridge/local_codex_smoke.py` 默认产出本地 `document.md` / `slides.md` / `whiteboard.mmd`
- `bridge/feishu_delivery.py` 默认把本地 `path` 当发布输入，而不是把 `remote` 当一等结果
- `bridge/codex_runner.py`、`scripts/process_feishu_event.py`、`bridge/console_demo_seed.py` 仍携带旧 MVP 语义

## Target Architecture

### 1. Execution Boundary

主执行链改为：

`Feishu IM -> GolemBot task shell -> Codex -> lark-cli / Feishu API -> task protocol -> Feishu result`

其中：

- GolemBot 负责会话入口、任务协议创建、线程绑定、回传组织。
- Codex 负责规划、选工具、直接执行飞书办公操作。
- Python bridge 负责协议持久化、轻量适配、兼容旧产物，不再默认替 Codex 做“二次办公”。

### 2. Task Protocol Boundary

保留现有任务协议目录：

- `request.md`
- `status.json`
- `artifacts.json`
- `control.jsonl`

但语义调整如下：

- `artifacts.json` 的 `items[]` 允许直接以 `remote` 为主，不要求本地中间文件先存在。
- 本地 `path` 变成可选证据或缓存，而不是默认主载体。
- 对飞书结果，至少记录 `provider=feishu`、对象 id、可打开 URL、必要的结构化元数据。

### 3. Tooling Strategy

主执行面采用：

1. `lark-cli`
2. `lark-cli api` / 直接 Feishu OpenAPI 补缺口
3. `lark-openapi-mcp` 作为旁路，而不是主链

不把 Presenton 放进主链。Presenton 可以作为“生成高质量 PPTX/PDF”的附加能力，但不应成为飞书 Slides 的默认落地方式。

## Component Roles

### GolemBot Layer

保留并收敛为四个职责：

1. IM ingress / egress
2. task/session/thread binding
3. task protocol 编排
4. 执行调度与结果回传

GolemBot 不再承担“本地文档生产器”或“办公结果二次加工器”的职责。

### Codex Layer

Codex 直接负责：

- 读取 `request.md` / `brief.json` / `control.jsonl`
- 选择 `lark-cli` / 飞书 API
- 创建或更新飞书文档 / Slides / 白板
- 把最终远端元数据回写到 `artifacts.json`

### Delivery Adapter Layer

`bridge/feishu_delivery.py` 从默认发布器降级为兼容适配器：

- 如果 `items[]` 已包含 `remote.provider=feishu`，则直接复用，不重复创建。
- 如果只有本地 `path`，才走 `lark_docs` / `lark_slides` / `lark_whiteboard` 做补发布。
- 白板发布必须支持“已有 document remote / whiteboard remote”的续改路径。

## Prompt Redesign

### Codex Task Prompt

`bridge/codex_task_runner.py` 的提示词需要明确：

- 主目标是完成真实办公任务，而不是产出本地 Markdown 占位物。
- 可以直接调用 `lark-cli`、飞书 API、Presenton 等现有 wheels。
- 任务完成标准是协议完整、结果可追踪，而不是“是否避免外部工具”。
- 对飞书远端结果，必须把 `remote` 元数据写入 `artifacts.json`。

### Request Markdown

`request.md` 保持“用户请求 + 上下文 + 验收要求”的职责，不再暗示“本地生成后再发布”。

## Frontend / Console Redesign

前端侧不再区分“会触发真实执行的 server-rendered cockpit”和“只写控制但不真正执行的 SPA 半成品”。

重构目标：

- 所有 append / retry / follow-up 操作都走同一套真实 backend 触发语义。
- 聊天区只消费协议层的统一投影，不区分旧 task console 与新 API 分支。
- 右侧 inspector 只展示用户可消费的飞书工件，不展示内部 plan / reply / 控制残留。

本次重构不追求先统一 UI 样式，先统一真实执行语义。

## Deletions and Downgrades

### Delete

- `bridge/codex_runner.py`
- `bridge/local_codex_smoke.py`
- `scripts/smoke_demo.py`

### Downgrade to Legacy-Only / Remove from Main Path

- `scripts/process_feishu_event.py`
- `bridge/console_demo_seed.py`

### Rewrite

- `bridge/codex_task_runner.py`
- `bridge/feishu_delivery.py`
- `bridge/golembot_office_loop.py`
- `bridge/server_app.py`
- `bridge/task_console_web.py`
- `scripts/task_console_web.py`

## Migration Strategy

### Phase 1

把执行默认值从 `local` 切到 `app-server` / `codex`，同时让 `artifacts.json` 支持远端主结果。

### Phase 2

把 `feishu_delivery` 改成 remote-aware 兼容适配器，允许 Codex 直接落远端对象。

### Phase 3

移除旧 smoke / demo / process entrypoint 对主链的干扰，补齐白板脚本包装。

### Phase 4

统一前端和 API 的真实执行语义，避免不同前端对同一任务产生不同 backend 行为。

## Risks

- `lark-cli` 的 Docs / Slides / Whiteboard 输入不是同一种表达层，Codex 需要更明确的 prompt 和薄包装。
- 已存在任务的 `artifacts.json` 可能同时混有本地 `path` 和远端 `remote`，兼容逻辑必须谨慎。
- 旧测试大量假设本地中间格式，需要同步重写。

## Success Criteria

满足以下条件才算完成：

1. 新任务默认不再走 `local` 生成器。
2. Codex 可直接生成飞书文档 / Slides / 白板，并把远端元数据写进 `artifacts.json`。
3. Python bridge 不再默认要求“本地产物 -> 后置发布”。
4. 前端 append / retry / follow-up 都能触发同一真实执行链。
5. 旧 smoke / demo / 遗留 prompt 不再污染主链。
