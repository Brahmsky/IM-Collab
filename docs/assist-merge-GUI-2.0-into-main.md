# 协助：将 GUI-2.0 上的提交分批 PR 到 `main`

**目标：** 不向 `main` 一次性大合并；与 **`GUI-2.0` 相对 `main` 的 5 个提交**对应 **4 个 PR 分支**（第 2 个 PR 内 **按序 cherry-pick 两笔**：`8acfcaf` → `3e0a850`）。  
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

### PR #2：`into-main/02-cockpit-web`（cherry-pick `8acfcaf`，再 `3e0a850`）

**标题**

```text
feat(web): 三栏 cockpit 初版与控制台路径、环回及 demo 种子修复（合并自 GUI-2.0）
```

**描述**

```markdown
## 摘要
在 `main` 已包含 `GUI/` 资产的前提下，本 PR **连续合入两笔** `GUI-2.0` 提交：先 **服务端 Tailwind 三栏 cockpit 初版**，再 **Web 控制台路径解析、IPv4/IPv6 环回、`--ensure-demo` 与 demo 种子**等修复，使本地可稳定演示。

## 变更范围
- 以 `8acfcaf`、`3e0a850` 的 diff 为准，通常涉及 `bridge/cockpit_console_html.py`、`bridge/task_console_web.py`、`scripts/task_console_web.py`、`bridge/console_demo_seed.py` 等。

## 依赖与顺序
- **须先合并 PR #1**。

## 验收建议
- 从仓库根或 `scripts/` 子目录启动均能解析 `tasks/`；`--ensure-demo` 可生成 `demo-local-smoke`；必要时 `--ipv4-only` 可规避 `localhost`/`::1` 问题。

## 来源
- 自 `GUI-2.0` 按序 cherry-pick：`8acfcaf`，然后 `3e0a850`
```

---

### PR #3：`into-main/03-readme-cockpit`（cherry-pick `cc95747`）

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
- **须先合并 PR #2**。

## 验收建议
- 按 README 命令可在本机拉起控制台并访问示例任务 URL。

## 来源
- 自 `GUI-2.0` cherry-pick：`cc95747`
```

---

### PR #4：`into-main/04-cockpit-align-docs`（cherry-pick `9797736`）

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
- **须先合并 PR #3**。

## 验收建议
- 本地 cockpit 视觉与 `GUI/code.html` 一致系；文档内链接可打开；`tests/test_task_console_web.py` 通过。

## 来源
- 自 `GUI-2.0` cherry-pick：`9797736`
```

**说明（不计入上述 4 个 PR）：** 若希望本协助清单 `docs/assist-merge-GUI-2.0-into-main.md` 出现在 `main` 上，而它又只在 `GUI-2.0` 的后续小提交里，可在 **PR #4 合并后** 另开一个小 PR（例如用 `git checkout GUI-2.0 -- docs/assist-merge-GUI-2.0-into-main.md`），见文末命令块。

---

## 当前进度（由协助脚本/操作生成）

| PR | 提交（按序） | 说明 | compare 分支 |
|----|----------------|------|----------------|
| **#1** | `42e0019` | GUI 2.0 静态资源与设计稿 | `into-main/01-gui-assets` |
| **#2** | `8acfcaf` → `3e0a850` | cockpit 初版 + 路径/环回/demo 修复（**同一分支两笔 pick**） | `into-main/02-cockpit-web` |
| **#3** | `cc95747` | README 控制台说明等 | `into-main/03-readme-cockpit` |
| **#4** | `9797736` | cockpit 与 GUI 对齐 + 进展文档等 | `into-main/04-cockpit-align-docs` |

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

同一分支上 **先后** cherry-pick 两笔（顺序不要反）：

```bash
git fetch origin
git checkout main
git pull origin main

git branch -D into-main/02-cockpit-web 2>/dev/null || true
git checkout -b into-main/02-cockpit-web main
git cherry-pick 8acfcaf
git cherry-pick 3e0a850
git push -u origin into-main/02-cockpit-web
```

开 PR：`main` ← `into-main/02-cockpit-web`。

---

## PR #3（在 PR#2 已合并后）

```bash
git fetch origin
git checkout main
git pull origin main

git branch -D into-main/03-readme-cockpit 2>/dev/null || true
git checkout -b into-main/03-readme-cockpit main
git cherry-pick cc95747
git push -u origin into-main/03-readme-cockpit
```

开 PR：`main` ← `into-main/03-readme-cockpit`。

---

## PR #4（在 PR#3 已合并后）

```bash
git fetch origin
git checkout main
git pull origin main

git branch -D into-main/04-cockpit-align-docs 2>/dev/null || true
git checkout -b into-main/04-cockpit-align-docs main
git cherry-pick 9797736
git push -u origin into-main/04-cockpit-align-docs
```

开 PR：`main` ← `into-main/04-cockpit-align-docs`。

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

## 可选：协助清单单独进 `main`（在 PR#4 已合并后）

把 `docs/assist-merge-GUI-2.0-into-main.md` 并进 `main`（从仍含该文件的 `GUI-2.0` 检出即可，**不必**与上面四笔一一对应）：

```bash
git fetch origin
git checkout main
git pull origin main

git branch -D into-main/optional-assist-merge-doc 2>/dev/null || true
git checkout -b into-main/optional-assist-merge-doc main
git checkout GUI-2.0 -- docs/assist-merge-GUI-2.0-into-main.md
git add docs/assist-merge-GUI-2.0-into-main.md
git commit -m "docs: add assist checklist for merging GUI-2.0 into main"
git push -u origin into-main/optional-assist-merge-doc
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
