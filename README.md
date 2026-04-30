# IM-Collab

IM-Collab 是比赛题目 **Agent-Pilot · 从 IM 对话到演示稿的一键智能闭环** 的实现仓库。

项目不重写 IM、文档、PPT、白板，也不自研 Agent 框架。我们复用飞书开放平台、lark-cli、Codex、superpowers、MCP/CLI 工具，把它们组织成一个可演示、可部署的办公协同闭环：

```text
飞书群聊/单聊
  -> lark-cli WebSocket 收事件
  -> Python Bridge 创建 tasks/<task_id>
  -> group-briefing 生成可追溯群聊 brief
  -> 如有冲突/待确认项，先回群确认并进入 waiting_for_user
  -> Codex + superpowers 规划、执行、验收
  -> lark-cli / Feishu API / Presenton 生成文档、Slides、白板
  -> artifacts.json / status.json 记录交付状态
  -> Python Bridge 回传飞书消息
```

一句话：**用户在飞书里说目标，Agent 驱动办公工具产出文档、演示稿、白板并回传。**

## 1. 先看这个

### 当前能跑什么

- 本地 smoke：不依赖飞书，验证任务协议。
- 飞书群聊：bot 进群后，@ bot 可触发任务。
- 群聊旁批汇总：群聊上下文会先生成 `brief.json` 和 `brief.md`，所有关键信息保留消息引用。
- 确认门控：brief 出现冲突或待确认问题时，先回群确认，不直接生成产物。
- 真实交付：可创建飞书文档、Slides、白板并回群。
- 控制台：CLI 和本地 Web 页面都可查看 `tasks/`、`events/`，也能追加指令、打断、重试、确认。
- Codex 后端：已有 `codex exec` 路径，也有 `codex app-server` 持久 session 路径。

### 当前还缺什么

- `app-server` 已是飞书 GolemBot 链路默认后端；手动脚本仍可显式指定 `local` 或 `codex`。
- 同一飞书会话已能复用 Codex thread；active turn 期间的新消息会写入 `control.jsonl` 并由 runner 转成 `turn/steer`。
- 控制台已有任务快照、thread/turn 可视、追加指令、打断、重试和确认；桌面 GUI 可在本地 Web console 外层再封装。
- 语音、离线、冲突合并、富媒体布局属于后续加分项。

### 和赛题是否对齐

对齐。赛题要求 IM 入口、Agent 主驾驶、文档、PPT 或自由画布、多端协同、GUI 辅助。赛题没有要求必须用 LangGraph，也没有禁止使用 Codex、飞书、开源工具或现成 CLI。我们的风险不是“用了轮子”，而是要避免看起来像简单脚本串 API。所以后续重点是：持久 session、续聊澄清、状态可观测、人工接管、真实办公产物。

## 2. 目录

```text
AGENTS.md                 Codex 项目规则：边界、任务协议、开发规则
落地方案.md               赛题要求与方案分析
bridge/                   Python Bridge 核心逻辑
scripts/                  启动、监听、消费、控制台脚本
skills/                   项目本地办公 skill
docs/                     调研、设计、后续计划
examples/                 本地演示输入
tests/                    单元测试
tasks/                    运行时任务目录，不提交
events/                   运行时事件目录，不提交
```

最常看的文件：

- `bridge/golembot_office_loop.py`：办公任务主循环。
- `bridge/codex_task_runner.py`：`codex exec` 路径。
- `bridge/codex_app_server.py`：Codex app-server JSON-RPC 客户端。
- `bridge/codex_app_server_task_runner.py`：app-server 任务 runner。
- `bridge/feishu_delivery.py`：发布本地产物到飞书。
- `scripts/run_event_consumer.py`：消费飞书事件。
- `scripts/run_golembot_office_task.py`：手动跑一个任务。
- `scripts/task_console.py`：查看任务状态，并给运行中任务追加指令或打断。

## 3. 环境

推荐：**Windows + WSL2 Ubuntu 22.04/24.04**。

Windows 原生理论上能跑测试和 smoke，但飞书监听、PTY、Codex app-server、长驻进程更建议放 WSL 里跑。

需要：

- Python 3.11+
- Node.js 18+
- npm
- Git
- Codex CLI
- lark-cli

## 4. 安装

以下命令在仓库根目录执行。项目内部开发命令建议加 `rtk`。

```bash
rtk python3 -m venv .venv
rtk .venv/bin/pip install -U pip
rtk .venv/bin/pip install -r requirements-dev.txt
```

安装飞书 CLI 和 skills：

```bash
rtk npm i -g @larksuite/cli
rtk npx skills add larksuite/cli -y -g
```

确认 Codex：

```bash
rtk codex --version
rtk codex app-server --help
```

## 5. 配飞书 Bot

队友第一次接项目时，最容易卡在这里。按下面顺序做。

### 5.1 创建飞书应用

进入飞书开放平台，创建一个企业自建应用：

1. 打开飞书开放平台开发者后台。
2. 创建企业自建应用。
3. 记录 `App ID` 和 `App Secret`，不要提交到仓库。
4. 在应用能力里启用机器人能力。
5. 设置应用可用范围，至少覆盖测试群成员。

### 5.2 配 lark-cli 应用信息

首次配置：

```bash
rtk lark-cli config init --new
```

按提示填入：

- App ID
- App Secret
- 租户/域名相关配置

检查：

```bash
rtk lark-cli auth status
rtk lark-cli doctor
```

说明：

- 事件监听和 bot 发消息主要走 bot 身份，依赖 App ID / App Secret。
- 如果要访问用户个人云空间等资源，才需要 user 身份授权。
- 不要把 App Secret 写进 README、提交记录或 issue。

### 5.3 开权限

至少需要这些方向的权限。具体 scope 以 `lark-cli doctor` 和报错里的 `permission_violations` 为准：

- 接收消息事件：`im:message:receive_as_bot`
- 发送/回复消息：IM message 相关权限
- 读取群聊信息/成员：IM chat 相关权限
- 创建/更新文档：Docs/Drive 相关权限
- 创建/更新演示稿：Slides 相关权限
- 创建/更新白板：Docs/Whiteboard 相关权限

开权限后通常需要发布应用版本，或在测试企业内启用新权限。

### 5.4 配事件订阅

在飞书开放平台应用后台：

1. 进入事件与回调。
2. 订阅方式选择 **使用长连接接收事件**。
3. 添加事件：`im.message.receive_v1`。
4. 确认权限里有 `im:message:receive_as_bot`。

本项目用 lark-cli 长连接监听，不需要自己搭公网 callback URL。

### 5.5 把机器人拉进群

在飞书客户端里：

1. 创建或打开测试群。
2. 添加机器人，选择你的应用 bot。
3. 群里 @ bot 发一条消息。
4. 如果普通消息没有事件，先用 @ bot 测试；很多配置下 bot 只对 @ 消息更稳定。

## 6. 本地先跑通

不接飞书，先确认仓库没坏：

```bash
rtk .venv/bin/python scripts/smoke_demo.py
rtk .venv/bin/python -m pytest
```

当前测试基线：

```text
91 passed
```

检查工具：

```bash
rtk .venv/bin/python scripts/check_tools.py
```

重点看 `codex`、`lark-cli`、`lark-im`、`lark-doc`、`lark-slides`、`lark-whiteboard` 是否 available。

## 7. 跑飞书链路

开两个终端。

终端 A：监听飞书事件。

```bash
rtk lark-cli event +subscribe \
  --event-types im.message.receive_v1,card.action.trigger \
  --compact \
  --quiet \
  --output-dir events/im
```

也可以用项目脚本：

```bash
rtk .venv/bin/python scripts/subscribe_feishu_events.py --output-dir events/im
```

终端 B：消费事件。

```bash
rtk .venv/bin/python scripts/run_event_consumer.py \
  --event-dir events/im \
  --dispatch golembot \
  --publish \
  --execute
```

然后在飞书群里 @ bot：

```text
根据刚才群聊内容，生成项目方案、8 页答辩 PPT 和白板流程图
```

参数说明：

- `--execute`：真的回复飞书；不加就是 dry-run。
- `--publish`：真的创建飞书文档/Slides/白板。
- 默认后端是 `app-server`。
- `--generator local`：本地 mock，最快。
- `--generator codex`：一次性 `codex exec` 兼容路径。
- `--generator app-server`：Codex 持久 session 主路径。
  同一 `session-key` 会复用已有 `codex_thread_id`，运行中会把 `active_turn_id` 写到 `tasks/task-bindings.json`。
此时同一飞书会话的新消息会追加到 `tasks/<task_id>/control.jsonl`，runner 轮询后调用 `turn/steer`。
- 确认卡片按钮会产生 `card.action.trigger`，Bridge 会写入 `control.jsonl`，并在“开始执行”动作中恢复 waiting task。

### 7.1 用构造群聊上下文跑测试

默认情况下，消费器会从真实飞书群聊读取上下文。开发和验收时可以显式传入标准后端群聊 fixture，避免每次都在群里手动一句句造数据：

```bash
rtk .venv/bin/python scripts/build_group_context_fixture.py \
  --input examples/scenarios/raw_feishu_events \
  --output /tmp/im-collab-context.json \
  --chat-id oc_demo
```

消费事件时指定：

```bash
rtk .venv/bin/python scripts/run_event_consumer.py \
  --event-dir events/im \
  --dispatch golembot \
  --publish \
  --execute \
  --context-fixture /tmp/im-collab-context.json
```

`--context-fixture` 支持单个 JSON、JSONL 或目录。只有传这个参数才走构造上下文；不传时仍走真实飞书群聊通路。

## 8. 手动跑一个任务

不走飞书事件，直接手动跑：

```bash
rtk .venv/bin/python scripts/run_golembot_office_task.py \
  --message "根据群聊生成项目方案、PPT 和白板" \
  --session-key "feishu:oc_demo" \
  --chat-id "oc_demo" \
  --sender-id "ou_demo" \
  --task-id "gb-local-demo" \
  --generator local
```

换真实 Codex：

```bash
rtk .venv/bin/python scripts/run_golembot_office_task.py \
  --message "根据群聊生成项目方案、PPT 和白板" \
  --session-key "feishu:oc_demo" \
  --chat-id "oc_demo" \
  --sender-id "ou_demo" \
  --task-id "gb-codex-demo" \
  --generator codex
```

主路径 app-server：

```bash
rtk .venv/bin/python scripts/run_golembot_office_task.py \
  --message "根据群聊生成项目方案、PPT 和白板" \
  --session-key "feishu:oc_demo" \
  --chat-id "oc_demo" \
  --sender-id "ou_demo" \
  --task-id "gb-app-server-demo" \
  --generator app-server
```

## 9. 看状态

任务目录：

```text
tasks/<task_id>/request.md       用户请求和群聊上下文
tasks/<task_id>/brief.json       source-grounded 群聊旁批汇总，机器可读
tasks/<task_id>/brief.md         source-grounded 群聊旁批汇总，人可读
tasks/<task_id>/status.json      queued/running/waiting_for_user/completed/failed
tasks/<task_id>/artifacts.json   文档、Slides、白板、摘要、下一步
tasks/<task_id>/delivery_card.json 交付消息卡片 payload
tasks/<task_id>/control.jsonl    追加指令、打断等运行中控制命令
```

看控制台快照：

```bash
rtk .venv/bin/python scripts/task_console.py --plain --limit 5
```

启动本地 Web 控制台：

```bash
rtk .venv/bin/python scripts/task_console_web.py --host 127.0.0.1 --port 8765
```

打开终端输出的 URL 后，可以查看任务、thread/turn、控制队列，并执行 append、interrupt、retry、ack。

只看失败：

```bash
rtk .venv/bin/python scripts/task_console.py --plain --state failed --limit 5
```

任务是否完成，只看 `status.json` 和 `artifacts.json`，不要靠终端输出猜。

给正在运行的任务追加指令：

```bash
rtk .venv/bin/python scripts/task_console.py append <task_id> --text "补充移动端入口说明"
```

打断正在运行的任务：

```bash
rtk .venv/bin/python scripts/task_console.py interrupt <task_id>
```

群聊任务会在生成正式产物前先写 `brief.json` 和 `brief.md`。后续文档、PPT、白板应优先使用这两个文件里的证据，不要直接凭原始群聊自由发挥。

如果 `brief.json` 中有 `conflict` 或 `open_question`，任务会进入 `waiting_for_user`，并写出 `confirmation.md`。同一群聊里的后续确认消息会写入 `control.jsonl`，后续继续执行或重试时 Codex 会读取这些确认信息。

如果用户在同一群聊里明确说“开始执行 / 开始生成 / 确认开始”，Bridge 会复用原 `task_id`，读取已经记录的确认信息，继续生成并发布产物。

等待确认的任务还会写出 `confirmation_card.json`，包含“开始执行”和“补充要求”按钮动作值。事件分发会优先用飞书 interactive 消息发送这张卡片；如果卡片文件不存在，才回退到 Markdown。

飞书卡片按钮回调会作为 `card.action.trigger` 事件进入同一个 consumer。`start_task` 会恢复对应的 waiting task；其他卡片动作会先进入 `control.jsonl`，供后续任务继续执行时读取。

完成发布的任务还会写出 `delivery_card.json`，包含文档和演示稿按钮。事件分发和手动 `deliver_task_to_feishu` 会优先发送这张 interactive 卡片；Markdown 交付文本仍保留为回退和控制台展示。

后续用户在同一活跃会话里继续发消息时，消息会优先作为运行中任务的追加指令；任务已完成后的修改需求会复用同一 Codex thread，并在 prompt 中带上已有 `artifacts.json`，尽量围绕原文档/Slides 修改而不是创建无关副本。

重试一个 GolemBot office 任务：

```bash
rtk .venv/bin/python scripts/task_console.py retry <task_id> --generator app-server --publish
```

确认一个失败或已处理的任务：

```bash
rtk .venv/bin/python scripts/task_console.py ack <task_id> --note "已确认，稍后复测"
```

## 10. 后续开发流程

按这个顺序做。

1. **app-server 主后端**
   - 一个飞书会话绑定一个 `codex_thread_id`。
   - 新任务走 `thread/start + turn/start`。
   - 后续消息复用同一个 thread。
   - active turn 运行中走 `control.jsonl -> turn/steer`。
   - 没有 active turn 时在同一个 thread 开新 `turn/start`。

2. **飞书续聊和澄清**
   - Agent 缺信息时自然反问。
   - `status.json` 标记 `waiting_for_user`。
   - 用户回复后继续原 task/thread。
   - 不向用户暴露 gateway、Codex backend、内部错误栈。

3. **可操作控制台**
   - 展示任务、事件、产物、错误、thread/turn。
   - 支持 append instruction、interrupt、retry、ack。
   - 控制动作复用 `tasks/<task_id>/control.jsonl`，由 Bridge 消费。
   - 本地 Web GUI 已复用同一底座；后续可按展示需要封装为桌面应用。

4. **比赛演示闭环**
   - 手机端群聊 @Agent。
   - 桌面端控制台显示任务运行。
   - 生成文档、Slides、白板。
   - 群聊收到交付链接。
   - 手机端/桌面端分别打开产物，展示多端同步。
   - 用户继续追问或要求修改，Agent 复用同一 session。

5. **加分项**
   - 语音入口。
   - Presenton/PPTX 真实文件。
   - 富媒体图片/表格。
   - 知识库归档。
   - 离线草稿和冲突合并。

## 11. 常见问题

### 监听不到消息

检查：

- bot 是否进群。
- 是否 @ bot。
- 开放平台是否启用长连接事件。
- 是否订阅 `im.message.receive_v1`。
- 是否有 `im:message:receive_as_bot`。
- `events/im/` 是否生成 JSON。

### 有事件但不回复

检查 consumer 是否带 `--execute`。

### 权限错误

看错误里的 `permission_violations` 和 `console_url`。  
bot 权限在开放平台开 scope；user 权限才用 `lark-cli auth login`。

### app-server 卡住

先检查：

```bash
rtk codex app-server --help
rtk .venv/bin/python -m pytest tests/test_codex_app_server_backend.py
```

### 任务失败

```bash
rtk .venv/bin/python scripts/task_console.py --plain --state failed --limit 5
rtk cat tasks/<task_id>/status.json
rtk cat tasks/<task_id>/request.md
```

## 12. 提交规则

不要提交：

- `.env` / `.env.*`
- `.codex/`
- `.agents/`
- `tasks/`
- `events/`
- 本机 token、App Secret、授权文件、真实事件数据

不要 `git add .`。用白名单：

```bash
rtk git add README.md .gitignore AGENTS.md bridge docs examples requirements-dev.txt scripts skills tests 落地方案.md
```

提交前：

```bash
rtk git status --short
rtk .venv/bin/python -m pytest
```
