# 协助：将 GUI-2.0 上的提交分批 PR 到 `main`

**目标：** 不向 `main` 一次性大合并；每个 PR 只带 **一笔** cherry-pick（顺序与 `GUI-2.0` 历史一致）。  
**约定远程：** `origin`；**上游默认分支：** `main`。

---

## 当前进度（由协助脚本/操作生成）

| 步骤 | 提交（短 SHA） | 说明 | 本地分支 | 远程 |
|------|----------------|------|----------|------|
| 1 | `42e0019` | GUI 2.0 静态资源与设计稿 | `into-main/01-gui-assets` | 待你 `git push`（若网络失败） |
| 2 | `8acfcaf` | 服务端 Tailwind cockpit 初版 | 待 PR1 合并后再建 | — |
| 3 | `3e0a850` | Web 路径、双栈、`--ensure-demo` | 同上 | — |
| 4 | `cc95747` | README 控制台说明等 | 同上 | — |
| 5 | `9797736` | cockpit 与 GUI 对齐 + 进展文档大包 | 同上 | — |
| 6（可选） | `9524278` | 本协助清单 `docs/assist-merge-GUI-2.0-into-main.md` | 在 PR#5 合并后 cherry-pick | — |

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

把本协助文档也并进 `main`（若你希望协作者从 `main` 就能看到该清单）：

```bash
git fetch origin
git checkout main
git pull origin main

git branch -D into-main/06-assist-merge-doc 2>/dev/null || true
git checkout -b into-main/06-assist-merge-doc main
git cherry-pick 9524278
git push -u origin into-main/06-assist-merge-doc
```

> 若 `9524278` 与当前 `GUI-2.0` 不一致，请用 `git log -1 --oneline GUI-2.0 -- docs/assist-merge-GUI-2.0-into-main.md` 取最新 SHA 替换。

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
