# 协助：将 GUI-2.0 上的提交分批 PR 到 `main`

**目标：** 不向 `main` 一次性大合并；每个 PR 只带 **一笔** cherry-pick（顺序与 `GUI-2.0` 历史一致）。  
**约定远程：** `origin`；**上游默认分支：** `main`。

---

## PR 标题与描述（可直接复制到 GitHub）

以下 **标题** 填 PR 标题栏；**描述** 填正文（可保留 Markdown）。每个 PR 的 **base 均为 `main`**，compare 为对应 `into-main/…` 分支。

### PR #1：`into-main/01-gui-assets`（cherry-pick `42e0019`）

**标题**

```text
feat(gui): 引入 GUI 2.0 静态稿与设计资产（合并自 GUI-2.0）
```

**描述**

```markdown
## 摘要
本 PR 将 **`GUI-2.0` 分支上的首笔 GUI 相关提交**（`42e0019`）合入 `main`，为后续 Web cockpit 提供统一的设计参照与静态资源。

## 变更范围
- 新增 `GUI/`：`code.html` 静态稿、`DESIGN.md`、预览图等设计资产。

## 依赖与顺序
- **无**前置 PR；请作为本系列 **第 1 个** 合并进 `main`。

## 验收建议
- 仓库内存在 `GUI/code.html` 等文件；打开静态 HTML 可浏览（**产品联调仍以 `task_console_web` 为准**，见静态稿头注释）。

## 来源
- 自 `GUI-2.0` cherry-pick：`42e0019`
```

---

### PR #2：`into-main/02-cockpit-web`（cherry-pick `8acfcaf`）

**标题**

```text
feat(web): 服务端渲染 Tailwind 三栏 cockpit（初版，合并自 GUI-2.0）
```

**描述**

```markdown
## 摘要
在 `main` 已包含 `GUI/` 资产的前提下，引入 **Python 服务端渲染** 的三栏任务 Web 控制台初版，与 GUI 稿同系（Tailwind + 布局骨架）。

## 变更范围
- `bridge/cockpit_console_html.py`、`bridge/task_console_web.py`、`scripts/task_console_web.py` 等与首版 cockpit 相关的实现（以本提交实际 diff 为准）。

## 依赖与顺序
- **须先合并 PR #1**（否则缺少 GUI 参照与约定路径）。

## 验收建议
- 本地执行 `python scripts/task_console_web.py --ensure-demo`（或按 README）可打开页面；任务列表与选中态可工作。

## 来源
- 自 `GUI-2.0` cherry-pick：`8acfcaf`
```

---

### PR #3：`into-main/03-web-fixes`（cherry-pick `3e0a850`）

**标题**

```text
fix(web): 控制台任务/events 路径与环回监听、本地 demo 种子（合并自 GUI-2.0）
```

**描述**

```markdown
## 摘要
修正本地 Web 控制台在 **工作目录不在仓库根**、以及 **IPv6 环回** 等环境下的可用性，并完善 `--ensure-demo` 等本地演示数据写入。

## 变更范围
- `scripts/task_console_web.py`、`bridge/console_demo_seed.py` 等（以本提交 diff 为准）。

## 依赖与顺序
- **须先合并 PR #2**。

## 验收建议
- 从 `scripts/` 子目录启动仍能解析 `tasks/`；必要时 `--ipv4-only` 可连上 `127.0.0.1`；`--ensure-demo` 可生成 `demo-local-smoke`。

## 来源
- 自 `GUI-2.0` cherry-pick：`3e0a850`
```

---

### PR #4：`into-main/04-readme-cockpit`（cherry-pick `cc95747`）

**标题**

```text
docs: README 补充 Web 控制台、--ensure-demo 与仓库根相对路径（合并自 GUI-2.0）
```

**描述**

```markdown
## 摘要
更新根目录 **README**，说明如何启动本地 Web 控制台、`--ensure-demo`、端口与路径解析等行为，便于协作者与评审复现。

## 变更范围
- 以 `README.md` 为主；若同提交含其它小清理（如误带流文件），以 diff 为准。

## 依赖与顺序
- **须先合并 PR #3**。

## 验收建议
- 按 README 命令可在本机拉起控制台并访问示例任务 URL。

## 来源
- 自 `GUI-2.0` cherry-pick：`cc95747`
```

---

### PR #5：`into-main/05-cockpit-align-docs`（cherry-pick `9797736`）

**标题**

```text
feat(cockpit): Web 控制台与 GUI 稿对齐并补充协作者进展文档（合并自 GUI-2.0）
```

**描述**

```markdown
## 摘要
将 **服务端 cockpit** 与 `GUI/code.html` 在布局、字体与信息结构上对齐；补充 **cockpit 进展与契约** 文档，并微调 README 中相关链接与排障说明。

## 变更范围
- `bridge/cockpit_console_html.py`、`GUI/code.html`（注释/说明）、`README.md`、`docs/2026-05-04-cockpit-ui-progress.md`、`docs/cockpit-ui-progress.md` 等（以本提交 diff 为准）。

## 依赖与顺序
- **须先合并 PR #4**。

## 验收建议
- 本地 cockpit 视觉与 `GUI/code.html` 一致系；文档内链接可打开；`tests/test_task_console_web.py` 通过。

## 来源
- 自 `GUI-2.0` cherry-pick：`9797736`
```

---

### PR #6（可选）：`into-main/06-assist-merge-doc`

**标题**

```text
docs: 增加 GUI-2.0 分批合入 main 的操作协助清单
```

**描述**

```markdown
## 摘要
将 `docs/assist-merge-GUI-2.0-into-main.md` 合入 `main`，便于协作者按步骤把 `GUI-2.0` 的剩余改动以多 PR 形式并入 `main`。

## 依赖与顺序
- **须先合并 PR #5**（或至少保证 `main` 上 cockpit 相关变更已稳定）。

## 说明
- 本文件可用「从 `GUI-2.0` 检出该文件再提交」的方式合入，见本文档前文「PR #6」命令块。
```

---

## 当前进度（由协助脚本/操作生成）

| 步骤 | 提交（短 SHA） | 说明 | 本地分支 | 远程 |
|------|----------------|------|----------|------|
| 1 | `42e0019` | GUI 2.0 静态资源与设计稿 | `into-main/01-gui-assets` | 待你 `git push`（若网络失败） |
| 2 | `8acfcaf` | 服务端 Tailwind cockpit 初版 | 待 PR1 合并后再建 | — |
| 3 | `3e0a850` | Web 路径、双栈、`--ensure-demo` | 同上 | — |
| 4 | `cc95747` | README 控制台说明等 | 同上 | — |
| 5 | `9797736` | cockpit 与 GUI 对齐 + 进展文档大包 | 同上 | — |
| 6（可选） | — | 仅把本协助清单文件拷进 `main`（见下「检出文件」法，避免追 SHA） | PR#5 合并后 | — |

在本地执行下面命令可再次确认顺序（从新到旧显示，**cherry-pick 时要从旧到新**）：

```bash
git log --oneline origin/main..GUI-2.0
```

---

## PR #1（已在本机准备好）

本地已执行：

```bash
git checkout main
git pull origin main
git checkout -b into-main/01-gui-assets main
git cherry-pick 42e0019
```

**请你网络正常时在本机执行：**

```bash
git push -u origin into-main/01-gui-assets
```

然后在 GitHub 开 PR：

- **base：** `main`
- **compare：** `into-main/01-gui-assets`
- 合并后 **不要删分支** 也可，删了不影响后续。

**Compare 链接模板（仓库名请按你的 fork 修改）：**

`https://github.com/Brahmsky/IM-Collab/compare/main...into-main/01-gui-assets?expand=1`

---

## PR #2（必须在 PR#1 已合并进 `main` 之后）

```bash
git fetch origin
git checkout main
git pull origin main

git branch -D into-main/02-cockpit-web 2>/dev/null || true
git checkout -b into-main/02-cockpit-web main
git cherry-pick 8acfcaf
git push -u origin into-main/02-cockpit-web
```

开 PR：`main` ← `into-main/02-cockpit-web`。

---

## PR #3（在 PR#2 已合并后）

```bash
git fetch origin
git checkout main
git pull origin main

git branch -D into-main/03-web-fixes 2>/dev/null || true
git checkout -b into-main/03-web-fixes main
git cherry-pick 3e0a850
git push -u origin into-main/03-web-fixes
```

开 PR：`main` ← `into-main/03-web-fixes`。

---

## PR #4（在 PR#3 已合并后）

```bash
git fetch origin
git checkout main
git pull origin main

git branch -D into-main/04-readme-cockpit 2>/dev/null || true
git checkout -b into-main/04-readme-cockpit main
git cherry-pick cc95747
git push -u origin into-main/04-readme-cockpit
```

开 PR：`main` ← `into-main/04-readme-cockpit`。

---

## PR #5（在 PR#4 已合并后）

```bash
git fetch origin
git checkout main
git pull origin main

git branch -D into-main/05-cockpit-align-docs 2>/dev/null || true
git checkout -b into-main/05-cockpit-align-docs main
git cherry-pick 9797736
git push -u origin into-main/05-cockpit-align-docs
```

开 PR：`main` ← `into-main/05-cockpit-align-docs`。

---

## Cherry-pick 冲突时

在对应 `into-main/…` 分支上：

```bash
git status
# 按提示改文件后
git add -A
git cherry-pick --continue
```

放弃本次 pick：

```bash
git cherry-pick --abort
```

---

## PR #6（可选，在 PR#5 已合并后）

把本协助文档并进 `main`（**不依赖 cherry-pick SHA**，从仍含该文件的 `GUI-2.0` 检出即可）：

```bash
git fetch origin
git checkout main
git pull origin main

git branch -D into-main/06-assist-merge-doc 2>/dev/null || true
git checkout -b into-main/06-assist-merge-doc main
git checkout GUI-2.0 -- docs/assist-merge-GUI-2.0-into-main.md
git add docs/assist-merge-GUI-2.0-into-main.md
git commit -m "docs: add assist checklist for merging GUI-2.0 into main"
git push -u origin into-main/06-assist-merge-doc
```

---

## 全部合并完成后

本地可选清理：

```bash
git fetch origin
git checkout main
git pull origin main
# 确认 main 已包含 GUI-2.0 全部能力后，再决定是否将 GUI-2.0 与 main 对齐或删除旧分支
```

---

*本页为协助清单；合并顺序错误会导致后续 cherry-pick 冲突增多，请严格在上一 PR 合并后再执行下一步。*
