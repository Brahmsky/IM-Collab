# IM-Collab

一个面向比赛场景的 Agent-Pilot 办公协同项目：

- 输入：飞书 IM 中的自然语言需求
- 编排：Codex + superpowers（唯一主编排层）
- 输出：文档、演示稿、白板等办公产物
- 回传：将交付结果回到飞书会话

## 这套项目解决什么问题

把传统的“聊天讨论 -> 手工整理文档 -> 手工做 PPT -> 手工回传”变成可自动执行的任务闭环。

核心边界：

- Python Bridge 负责消息入口、任务目录、状态与产物协议、外部工具调用
- Codex + superpowers 负责规划、追问、执行、验收
- 飞书、lark-cli、Presenton、GolemBot 都是被调用的工具层

## 给零基础同学的上手路径

如果你对配置和部署完全不熟，按下面顺序做就行：

1. 跑通本地离线 Smoke（不依赖飞书账号）
2. 检查工具可用性（Codex/lark-cli/skills）
3. 配置飞书环境变量，跑事件监听和消费
4. 可选：接入 GolemBot 网关，走比赛演示链路

## 目录速览

- `bridge/`: 任务协议、事件处理、投递与交付核心逻辑
- `scripts/`: 启动脚本和演示脚本
- `skills/`: 办公场景技能
- `tasks/`: 任务目录（运行时产物，不提交）
- `events/`: 事件文件目录
- `tests/`: 单元测试
- `docs/`: 参考文档与设计说明

## 0. 环境准备

### 0.1 系统依赖

建议 Linux/macOS，推荐：

- Python 3.11+
- Node.js 18+
- npm
- Git

### 0.2 创建 Python 虚拟环境

```bash
rtk python3 -m venv .venv
rtk .venv/bin/pip install -U pip
rtk .venv/bin/pip install -r requirements-dev.txt
```

### 0.3 安装关键 CLI

1) Codex CLI（需你本机已可用 `codex` 命令）

2) 飞书 CLI：

```bash
rtk npm i -g @larksuite/cli
```

3) 安装飞书 skills：

```bash
rtk npx skills add larksuite/cli -y -g
```

4) 可选：GolemBot（用于网关链路）

```bash
rtk npm exec --yes --package golembot@0.46.0 -- golembot --version
```

## 1. 本地离线 Smoke（先做这个）

这个模式不依赖飞书密钥，适合第一次上手。

```bash
rtk .venv/bin/python scripts/smoke_demo.py
```

成功后会生成：

- `tasks/demo-local-smoke/request.md`
- `tasks/demo-local-smoke/status.json`
- `tasks/demo-local-smoke/artifacts.json`
- 以及 `document.md`、`slides.md`、`whiteboard.mmd`

再跑测试确认本地没问题：

```bash
rtk .venv/bin/pytest -q
```

## 2. 工具体检

```bash
rtk .venv/bin/python scripts/check_tools.py
```

你会看到 JSON 输出，关注：

- `binaries.codex.available`
- `binaries.lark-cli.available`
- `skills.lark-im/lark-doc/lark-slides/lark-whiteboard.available`

如果是 `false`，先补安装再继续。

## 3. 接飞书最小链路

### 3.1 飞书认证

先做一次登录与检查：

```bash
rtk lark-cli auth login
rtk lark-cli auth status
rtk lark-cli doctor
```

### 3.2 订阅 IM 事件

```bash
rtk .venv/bin/python scripts/subscribe_feishu_events.py --output-dir events/im
```

这会在 `events/im/` 目录持续写入事件 JSON。

### 3.3 启动事件消费

本地处理（默认）:

```bash
rtk .venv/bin/python scripts/run_event_consumer.py --execute --once
```

持续运行：

```bash
rtk .venv/bin/python scripts/run_event_consumer.py --execute
```

说明：

- `--execute` 表示发送真实回复
- 不加 `--execute` 时为 dry-run 回复
- `--dispatch local` 走本地处理
- `--dispatch golembot` 转发到 GolemBot

## 4. 比赛演示链路（lark-cli 入站 + GolemBot 编排）

先打印三条标准启动命令：

```bash
rtk .venv/bin/python scripts/print_demo_chain.py
```

按输出开 3 个终端分别执行：

1. GolemBot gateway
2. Feishu listener
3. Event consumer（带 `--dispatch golembot --generator codex --publish --execute`）

## 5. 运行时文件协议（非常重要）

每个任务目录应包含：

- `request.md`
- `status.json`
- `artifacts.json`
- `tmux.log`（可选）

状态只允许：

- `queued`
- `running`
- `waiting_for_user`
- `completed`
- `failed`

任务是否完成，以 `artifacts.json` + `status.json` 为准，不以终端输出为准。

## 6. 常见问题

1) `codex: command not found`

先完成 Codex CLI 安装并确认 PATH 可见。

2) `lark-cli` 权限错误

重新 `lark-cli auth login`，并检查飞书应用权限范围。

3) 监听到了事件但没有回复

检查 `run_event_consumer.py` 是否带了 `--execute`。

4) 任务一直不完成

优先看 `tasks/<task_id>/status.json` 的 `state` 和 `error` 字段。

## 7. 部署建议（团队内部）

当前仓库更适合先以“单机守护进程”方式部署：

- 进程 A：`scripts/subscribe_feishu_events.py`
- 进程 B：`scripts/run_event_consumer.py`
- 可选进程 C：GolemBot gateway

建议使用 tmux/systemd/supervisor 做常驻，日志按天切分。

## 8. 提交规范（避免泄露本机私有信息）

不要提交这类文件：

- `.env`、`.env.*`
- `.codex/`
- `.agents/`
- `tasks/` 运行产物
- `.experiments/` 本地实验目录

本仓库 `.gitignore` 已包含以上规则。

建议用“白名单 add”提交：

```bash
rtk git add README.md .gitignore bridge docs events examples requirements-dev.txt scripts skills tests 落地方案.md
rtk git commit -m "docs: add teammate onboarding and deployment guide"
rtk git push origin HEAD
```

如果你不确定某个文件该不该提交，先跑：

```bash
rtk git status --short
```

确认没有本机私有内容后再 push。
