# 前端 Mock 大筛查

日期：2026-05-04

范围：`bridge/cockpit_console_html.py`、`bridge/task_console_web.py`、`scripts/task_console_web.py`。本次筛查按“每个可见组件/交互是否有真实后端语义”逐项检查，不把“页面能显示”当作通过标准。

## 判定标准

- **真实**：读取或写入项目已有协议文件、服务状态或真实后端通道，例如 `tasks/*/status.json`、`artifacts.json`、`request.md`、`control.jsonl`、`task-bindings.json`。
- **半真实**：数据来自真实协议，但文案、状态颗粒度或交互入口仍有占位成分。
- **占位/Mock**：点击没有真实功能，或展示内容不是从后端状态/任务协议推导，而是为了像截图而写死。
- **语气不合格**：把内部实现、错误归属或演示说明直接暴露给用户，破坏 Agent-Pilot 产品语义。

## 组件逐项筛查

| 区域 | 功能点 | 当前数据/行为来源 | 判定 | 问题 | 改造要求 |
| --- | --- | --- | --- | --- | --- |
| 左侧品牌 | `Agent-Pilot / Precision Cockpit` | 静态产品名 | 真实 | 可接受，属于产品壳层 | 后续按最终命名统一即可 |
| 搜索框 | `Search sessions...` | GET `q`，调用 `_filter_tasks` | 半真实 | 已有过滤，但早期只覆盖 `task_id/session_key/summary/thread/state`，不完整 | 必须覆盖 session title、chat name、artifact label/value |
| 新建任务按钮 | 打开说明弹窗 | `<dialog>`，不创建任务 | 半真实 | 标签叫“新建任务”，实际是“如何从飞书/CLI 创建任务”的说明 | 短期保留但文案要说明入口语义；长期接入 `/new` 或禁用 |
| 插件 | 未展示 | 无后端动作 | 已收口 | 无真实功能时不在前端展示 | 等有真实插件 registry 再恢复 |
| 自动化 | 未展示 | 无后端动作 | 已收口 | 无真实功能时不在前端展示 | 等有真实 automation model 再恢复 |
| 任务分组 | 飞书群组折叠 | `TaskSummary.chat_name/chat_id/session_key` | 真实 | 组名 fallback 仍可能暴露技术 ID | 后续用 Feishu chat metadata 补全名称 |
| 会话列表 | session title、选中态、相对时间 | `task-bindings.json`、`status.updated_at` | 真实 | 已具备基础语义 | 保持；后续增加会话生命周期状态 |
| 会话展开状态 | group open state | `localStorage` | 真实本地 UI 状态 | 不是后端状态，但语义合理 | 保持 |
| 会话重命名 | inline rename | POST `rename_session` 写 `task-bindings.json` | 真实 | 此前只改左侧，不改顶部标题；已修复 | 后续可写审计事件 |
| 会话删除 | archive task dir | POST `delete_session` 移动到 `tasks/.archived` | 真实但高风险 | “删除 session”实际是归档任务目录，未二次确认 | 加确认与撤销策略 |
| 顶部标题 | 选中会话标题 | 此前优先 summary；已改为优先 `session_title` | 真实 | 已修复语义不完整 | 保持 |
| 顶部状态 badge | DONE/ACTIVE 等 | `status.state` | 真实 | 英文状态和中文界面不一致 | 改为中文或产品统一状态标签 |
| 顶部全屏 | Fullscreen API | 浏览器 API | 真实 | 可用 | 保持 |
| 顶部刷新 | GET 当前任务 | 链接刷新 | 真实 | 可用 | 保持 |
| 顶部更多 | 只显示刷新和任务 ID | HTML details | 半真实 | 功能过薄但不假 | 后续增加复制 ID、打开任务目录等真实操作 |
| 中央用户气泡 | 原始请求与后续补充 | `request.md -> ## User Message` + `control.jsonl append_instruction` | 真实 | 必须按时间顺序展示真实用户轮次，不能用 `summary` 冒充用户输入 | 已改为聊天窗口里的用户气泡 |
| 中央助手气泡 | 已完成任务的交付回复 | `artifacts.summary`、`status.json`、`artifacts.json` | 真实投影 | 只能展示已经由任务协议产生的结果；没有新结果时不能伪造回答 | 已改为完成回合的助手气泡，清单和工件作为附件区域 |
| 中央待回复标记 | 完成后又有新补充 | `control.jsonl append_instruction.timestamp > status.updated_at` | 真实投影 | 不能把用户刚追加的消息显示成已处理 | 已改为“待回复”状态和中性待处理标记 |
| 执行清单 | 读取上下文/brief/Codex/工件/回传 | `_step_class(status/artifacts)` | 半真实 | 粗粒度来自真实状态，但步骤名称仍是固定协议里程碑 | 短期可接受；长期接入真实 run event / Codex turn event |
| 工件卡片 | document/slides/whiteboard | `artifact_outputs` | 真实 | 类型图标由 label 推断，略脆弱 | 后续从 `artifacts.items[].kind/type` 直接派生 |
| 底部附件按钮 | paperclip disabled | 静态禁用 | 半真实 | 文案含 MVP，产品语气差 | 改为“附件请在飞书会话发送”或隐藏 |
| 底部输入框 | 追加指令 | 异步 POST 写 `control.jsonl`，并按任务状态触发真实 Codex 后端 | 真实 | 此前普通 HTML POST 会整页刷新；Enter 只触发旧提交路径；已完成任务收到补充后没有继续执行 Codex | 已改为 fetch 异步发送、Enter 发送、Shift+Enter 换行；发送成功后追加真实用户气泡、自动滚到底部，并打开 `/api/task-stream` 接收任务快照 |
| 右侧详情 | 状态/来源/创建/任务 ID | `TaskSummary` | 真实 | 来源显示 `session_key`，对用户偏技术 | 后续显示群名，技术 ID 收到展开区 |
| 运维字段 | Codex thread/turn/control | `task-bindings.json/control.jsonl/ack.json` | 真实 | 属于高级信息 | 保持折叠 |
| 右侧打断 | POST `interrupt` 写 `control.jsonl` | 真实 | 只能在运行态出现 | 已按状态约束，完成/待回复时不展示 |
| 右侧确认 | 写 `ack.json` | 真实 | 只能在 `waiting_for_user` 出现 | 已按状态约束 |
| 右侧 retry / 执行补充 | 调 `retry_golembot_task` / Codex app-server | 真实 | generator 下拉暴露 `local/app-server/codex`，对产品用户过于底层 | 普通模式隐藏底层参数；待回复时显示“执行补充”；底部发送补充时会自动触发真实 Codex 后端继续执行 |
| 发布到飞书 | retry publish flag | 真实参数 | 半真实 | 不是普通用户应理解的动作 | 已从普通界面隐藏；后续改为“回传到原会话”并按权限显示 |
| 时间线 | control/events 文件 | `control.jsonl` + latest events | 真实 | 只是文本 dump，不是产品化事件流 | 后续结构化展示 |
| 空状态 | “请先从飞书会话触发任务” | 静态文案 | 已收口 | 已移除 demo/MVP/CLI 说明 | 后续可接入真实新任务入口 |
| 错误页 | traceback | Python traceback | 真实调试 | 对产品用户不合适 | 开发模式保留，产品模式显示简化错误 |

## 结论

当前前端不是“全部 mock”：任务列表、状态、工件、重命名、删除、追加、打断、确认、重试都已经接入真实本地后端协议。

但中央工作区此前是最大问题：

- 用户气泡使用 `artifacts.summary`，不是原始请求。
- 助手回复是静态“收到，正在...”。
- 追加指令后显示顶部 flash，或者被错误地画成已处理的聊天泡。
- 文本框不支持聊天应用的基础行为：Enter 发送、Shift+Enter 换行。
- 发送后整页刷新，破坏聊天窗口连续性。
- 已完成任务收到 GUI 补充后只写本地 JSON，没有自动接入真实 Codex app-server 后端继续执行。
- checklist 只是粗粒度协议状态，不是 Codex 实时输出。

因此，中央工作区必须是聊天窗口，但只能投影真实 `request.md + control.jsonl + status.json + artifacts.json`。有真实完成结果时显示助手气泡；完成后出现新补充时显示用户气泡和“待回复”，同时触发真实 Codex 后端继续执行，不伪造新的 assistant 回复。

## 立即整改清单

1. GUI append 写入 `control.jsonl` 时补充 `source=gui`、`kind=operator_followup`，并取消顶部成功 flash。
2. 中央用户气泡读取 `request.md -> ## User Message`。
3. 中央用户后续补充读取最近 `control.jsonl append_instruction`，尤其是完成后的补充。
4. 助手气泡由 `status.state`、`artifact_outputs` 和 pending follow-ups 推导，不再固定“收到，正在...”。
5. 顶部标题优先使用 `session_title`，与侧栏重命名保持一致。
6. 搜索覆盖 session title、chat name、artifact label/value。
7. 把无真实后端动作的 `href="#"` 控件隐藏。
8. 所有成功类表单提交不再弹绿色条，避免把操作台变成后台管理系统；失败仍保留错误反馈。
9. 底部输入框支持 Enter 发送、Shift+Enter 换行。
10. 右侧操作按任务状态显示：运行态打断，待确认态确认，完成后补充态执行补充。
11. 底部发送改为异步 POST：不整页刷新，成功后追加真实用户气泡并自动滚到底部。
12. 异步发送后接入真实 Codex 后端：运行中任务通过既有控制通道进入活跃回合，已完成/等待/失败任务触发 Codex app-server 后续执行。
13. GUI 打开 `/api/task-stream`，用 SSE 快照更新聊天区；当前是任务协议级流，后续可替换为 Codex raw event 级实时流。

## 后续必须避免

- 不再为了像参考图而补静态文字。
- 不把 `summary` 当用户输入。
- 不把后续补充显示成已经被 assistant 回答的聊天泡。
- 没有真实 assistant 事件源时，不在中央区伪造 assistant 回复。
- 不给用户显示“已调用 xxx 后端”“这是 gateway 错了”这类内部实现话术。
- 不新增看起来可点但无真实动作的控件。
- 不用正则/关键词去猜用户意图；GUI 消息直接进入同一控制/执行通道。
