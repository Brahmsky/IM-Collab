"""Server-rendered Agent-Pilot cockpit UI (aligned with GUI/code.html design tokens)."""

from __future__ import annotations

import json
from collections import OrderedDict
from html import escape
from pathlib import Path
from urllib.parse import quote

from bridge.task_index import EventSummary, TaskSummary


def _state_label(state: str) -> str:
    return {
        "queued": "排队中",
        "running": "运行中",
        "waiting_for_user": "等待确认",
        "completed": "已完成",
        "failed": "失败",
    }.get(state, state)


def _state_label_en(state: str) -> str:
    return {
        "queued": "QUEUED",
        "running": "ACTIVE",
        "waiting_for_user": "WAITING",
        "completed": "DONE",
        "failed": "FAILED",
    }.get(state, state.upper())


def _step_row(task: TaskSummary, step: str, label: str) -> str:
    cls = _step_class(task, step)
    if cls == "failed":
        icon = "error"
        row_cls = "text-error font-medium"
        extra = ""
    elif cls == "done":
        icon = "check_box"
        row_cls = "line-through text-text-secondary"
        extra = ""
    elif cls == "active":
        icon = "progress_activity"
        row_cls = "text-text-primary font-medium"
        extra = (
            '<span class="ml-2 px-2 py-0.5 rounded text-[12px] font-medium bg-tag-bg-blue text-primary">进行中</span>'
        )
    else:
        icon = "check_box_outline_blank"
        row_cls = "text-text-primary"
        extra = ""

    spin = ' animate-spin' if cls == "active" else ""
    return f"""<div class="flex items-center gap-2 text-[14px] {row_cls}">
<span class="material-symbols-outlined text-[18px]{spin}">{icon}</span>
<span>{escape(label)}</span>{extra}
</div>"""


def _step_class(task: TaskSummary, step: str) -> str:
    state = task.state
    if state == "failed":
        return "failed"
    if step == "context":
        return "done"
    if step == "brief":
        return "done" if state in {"running", "waiting_for_user", "completed"} else "todo"
    if step == "execution":
        return "done" if state == "completed" else ("active" if state == "running" else "todo")
    if step == "artifacts":
        if task.artifact_outputs or state == "completed":
            return "done"
        return "active" if state == "running" else "todo"
    if step == "delivery":
        return "done" if state == "completed" else ("active" if state == "running" else "todo")
    return "todo"


def _filter_tasks(tasks: list[TaskSummary], q: str) -> list[TaskSummary]:
    needle = q.strip().lower()
    if not needle:
        return tasks
    out: list[TaskSummary] = []
    for t in tasks:
        hay = " ".join(
            [
                t.task_id,
                t.session_key or "",
                t.summary or "",
                t.codex_thread_id or "",
                t.state or "",
            ]
        ).lower()
        if needle in hay:
            out.append(t)
    return out


def _short_created_display(iso: str) -> str:
    if not (iso or "").strip():
        return "—"
    s = iso.strip().replace("T", " ", 1)
    if "+" in s:
        s = s.split("+", 1)[0].strip()
    if s.endswith("Z"):
        s = s[:-1].strip()
    return s[:16] if len(s) >= 16 else s


def _cockpit_header_title(t: TaskSummary) -> str:
    raw = (t.summary or "").strip()
    if raw:
        line = raw.split("\n", 1)[0].strip()
        if len(line) > 48:
            return line[:47] + "…"
        return line
    tid = t.task_id
    return tid[:48] + ("…" if len(tid) > 48 else "")


def _inspector_status_value_html(t: TaskSummary) -> str:
    if t.state == "running":
        return (
            '<span class="px-2 py-0.5 rounded bg-tag-bg-blue text-primary text-[12px] font-medium '
            'flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse">'
            f'</span>{escape("进行中")}</span>'
        )
    if t.state == "waiting_for_user":
        return (
            f'<span class="px-2 py-0.5 rounded bg-[#FFF0E6] text-[#FA6400] text-[12px] font-medium">'
            f"{escape(_state_label(t.state))}</span>"
        )
    if t.state == "completed":
        return (
            f'<span class="px-2 py-0.5 rounded bg-[#E8F8F2] text-success text-[12px] font-medium">'
            f"{escape(_state_label(t.state))}</span>"
        )
    if t.state == "failed":
        return (
            f'<span class="px-2 py-0.5 rounded bg-[#FFECE8] text-error text-[12px] font-medium">'
            f"{escape(_state_label(t.state))}</span>"
        )
    return f'<span class="text-text-primary font-medium">{escape(_state_label(t.state))}</span>'


def _build_inspector_primary_rows_html(t: TaskSummary) -> str:
    tid_mono = (
        f'<span class="text-text-primary bg-tag-bg-gray px-1.5 py-0.5 rounded font-mono text-[12px]">'
        f"{escape(t.task_id)}</span>"
    )
    rows: list[tuple[str, str]] = [
        ("状态", _inspector_status_value_html(t)),
        ("来源", escape(t.session_key or "—")),
        ("创建于", escape(_short_created_display(t.created_at))),
        ("任务 ID", tid_mono),
    ]
    out = []
    for label, val_html in rows:
        out.append(
            f"""<div class="flex justify-between items-center text-[14px] gap-4">
<span class="text-text-secondary shrink-0">{escape(label)}</span>
<span class="flex justify-end text-right break-all min-w-0">{val_html}</span>
</div>"""
        )
    tech = f"""<details class="mt-2 border border-border rounded-lg p-3 bg-surface-hover/30">
<summary class="text-[12px] font-medium text-text-secondary cursor-pointer">运维与同步字段</summary>
<div class="mt-3 space-y-2 text-[13px] text-text-primary">
<div class="flex justify-between gap-2"><span class="text-text-secondary">Codex 线程</span><span class="font-mono text-right break-all">{escape(t.codex_thread_id or "—")}</span></div>
<div class="flex justify-between gap-2"><span class="text-text-secondary">活跃回合</span><span class="font-mono text-right break-all">{escape(t.active_turn_id or "—")}</span></div>
<div class="flex justify-between gap-2"><span class="text-text-secondary">控制队列</span><span>{escape(str(t.control_count) if t.control_count else "—")}</span></div>
<div class="flex justify-between gap-2"><span class="text-text-secondary">最新操作</span><span class="break-all">{escape(t.last_control_type or "—")}</span></div>
<div class="flex justify-between gap-2"><span class="text-text-secondary">确认人</span><span>{escape(t.ack_operator or "—")}</span></div>
<div class="flex justify-between gap-2"><span class="text-text-secondary">更新时间</span><span class="tabular-nums">{escape(t.updated_at or "—")}</span></div>
</div>
</details>"""
    return "".join(out) + tech


def _group_by_session(tasks: list[TaskSummary]) -> OrderedDict[str, list[TaskSummary]]:
    groups: OrderedDict[str, list[TaskSummary]] = OrderedDict()
    for t in tasks:
        key = _task_group_label(t)
        groups.setdefault(key, []).append(t)
    return groups


def _task_group_label(t: TaskSummary) -> str:
    if t.chat_name.strip():
        return t.chat_name.strip()
    if t.chat_id.strip():
        return f"feishu:{t.chat_id.strip()}"
    session_key = (t.session_key or "").strip()
    if session_key:
        parts = session_key.split(":")
        if len(parts) >= 2 and parts[1]:
            return f"{parts[0]}:{parts[1]}"
        return session_key
    return "未绑定会话"


def _session_display_title(t: TaskSummary) -> str:
    title = (t.session_title or "").strip()
    if title:
        return title
    raw = (t.summary or "").strip().split("\n", 1)[0].strip()
    if raw:
        return raw[:22] + ("…" if len(raw) > 22 else "")
    return t.task_id


def _session_menu_html(t: TaskSummary, search_query: str) -> str:
    tid = escape(t.task_id)
    session_key = escape(t.session_key or "")
    title = escape(_session_display_title(t), quote=True)
    q = escape(search_query, quote=True)
    return f"""<details class="relative session-actions opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
<summary class="list-none w-7 h-7 rounded-md hover:bg-white/80 flex items-center justify-center cursor-pointer text-text-secondary" aria-label="会话操作">
<span class="material-symbols-outlined text-[18px]">more_horiz</span>
</summary>
<div class="absolute right-0 top-full mt-1 w-56 bg-white border border-border rounded-lg shadow-lg p-2 z-50">
<form method="post" class="space-y-2">
<input type="hidden" name="action" value="rename_session">
<input type="hidden" name="task_id" value="{tid}">
<input type="hidden" name="session_key" value="{session_key}">
<input type="hidden" name="redirect_task" value="{tid}">
<input type="hidden" name="q" value="{q}">
<label class="block text-[12px] text-text-secondary">重命名</label>
<input name="session_title" value="{title}" required class="w-full border border-border rounded-md px-2 py-1.5 text-[13px] text-text-primary">
<button type="submit" class="w-full rounded-md bg-primary text-white px-2 py-1.5 text-[13px] font-medium">保存名称</button>
</form>
<form method="post" class="mt-2 pt-2 border-t border-border">
<input type="hidden" name="action" value="delete_session">
<input type="hidden" name="task_id" value="{tid}">
<input type="hidden" name="session_key" value="{session_key}">
<button type="submit" class="w-full rounded-md px-2 py-1.5 text-[13px] text-error hover:bg-[#FFECE8] text-left">删除 session</button>
</form>
</div>
</details>"""


def _pick_selected(tasks: list[TaskSummary], selected_task_id: str | None) -> TaskSummary | None:
    if not tasks:
        return None
    if selected_task_id:
        for t in tasks:
            if t.task_id == selected_task_id:
                return t
    return tasks[0]


def _artifact_kind(label: str) -> tuple[str, str]:
    u = label.upper()
    if "SLIDE" in u or "PPT" in u or "演示" in label:
        return "co_present", "pptx"
    if "白板" in label or "WHITEBOARD" in u:
        return "dashboard", "board"
    if "DOC" in u or "文档" in label:
        return "description", "docx"
    return "article", "file"


def _artifact_card_main(label: str, value: str) -> str:
    icon, kind = _artifact_kind(label)
    safe_label = escape(label)
    if value and value.startswith("http"):
        safe_href = escape(value, quote=True)
        return f"""<a href="{safe_href}" target="_blank" rel="noopener noreferrer" class="bg-white border border-border rounded-xl p-4 flex flex-col gap-2 relative overflow-hidden group hover:shadow-md transition-shadow cursor-pointer no-underline text-inherit">
<div class="absolute left-0 top-0 bottom-0 w-1 bg-primary"></div>
<div class="flex justify-between items-start">
<div class="flex items-center gap-1.5 text-primary">
<span class="material-symbols-outlined text-[18px]">{icon}</span>
<span class="text-[12px] font-medium uppercase">{escape(kind)}</span>
</div>
<span class="material-symbols-outlined text-[16px] text-primary">open_in_new</span>
</div>
<div class="mt-1">
<h4 class="font-medium text-[14px] text-text-primary truncate">{safe_label}</h4>
<p class="text-[12px] text-text-secondary mt-1">已生成，点击打开</p>
</div>
</a>"""
    if value:
        return f"""<div class="bg-white border border-border rounded-xl p-4 flex flex-col gap-2 relative overflow-hidden">
<div class="absolute left-0 top-0 bottom-0 w-1 bg-border"></div>
<div class="flex items-center gap-1.5 text-primary">
<span class="material-symbols-outlined text-[18px]">{icon}</span>
<span class="text-[12px] font-medium uppercase">{escape(kind)}</span>
</div>
<div class="mt-1">
<h4 class="font-medium text-[14px] text-text-primary truncate">{safe_label}</h4>
<p class="text-[12px] text-text-secondary mt-1">{escape(value)}</p>
</div>
</div>"""
    return f"""<div class="bg-white border border-border rounded-xl p-4 flex flex-col gap-2 relative overflow-hidden opacity-90">
<div class="absolute left-0 top-0 bottom-0 w-1 bg-border group-hover:bg-primary transition-colors"></div>
<div class="flex justify-between items-start">
<div class="flex items-center gap-1.5 text-primary">
<span class="material-symbols-outlined text-[18px]">{icon}</span>
<span class="text-[12px] font-medium uppercase">{escape(kind)}</span>
</div>
<span class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse mt-1.5"></span>
</div>
<div class="mt-1">
<h4 class="font-medium text-[14px] text-text-primary truncate">{safe_label}</h4>
<p class="text-[12px] text-text-secondary flex items-center gap-1 mt-1">
<span class="material-symbols-outlined text-[14px] animate-spin">progress_activity</span>
待生成
</p>
</div>
</div>"""


def _append_form(task_id: str) -> str:
    tid = escape(task_id)
    return f"""<form method="post" class="max-w-4xl mx-auto bg-white border border-border rounded-xl shadow-sm focus-within:ring-1 focus-within:ring-primary focus-within:border-primary transition-all flex items-end p-2 gap-2">
<input type="hidden" name="action" value="append">
<input type="hidden" name="task_id" value="{tid}">
<input type="hidden" name="redirect_task" value="{tid}">
<label class="p-2 text-text-secondary shrink-0 cursor-not-allowed opacity-70" title="MVP：附件请通过飞书 IM 发送；此处仅文本追加">
<input type="file" class="hidden" disabled tabindex="-1"/>
<span class="material-symbols-outlined text-[20px]">attach_file</span>
</label>
<textarea name="text" required rows="1" placeholder="添加指令..." class="w-full bg-transparent border-none resize-none focus:ring-0 text-[14px] py-2 px-2 max-h-32 placeholder-text-secondary text-text-primary outline-none"></textarea>
<button type="submit" class="w-9 h-9 rounded-lg bg-primary text-white hover:bg-primary-hover flex items-center justify-center transition-colors shrink-0 mb-0.5 mr-0.5" title="发送">
<span class="material-symbols-outlined text-[18px]">send</span>
</button>
</form>"""


def _ops_form(task_id: str) -> str:
    tid = escape(task_id)
    return f"""<div class="space-y-3 pt-2 border-t border-border">
<form method="post" class="flex flex-wrap gap-2 items-center">
<input type="hidden" name="task_id" value="{tid}">
<input type="hidden" name="redirect_task" value="{tid}">
<button type="submit" name="action" value="interrupt" class="px-3 py-2 rounded-lg bg-[#FFECE8] text-error text-[13px] font-medium hover:opacity-90">打断</button>
</form>
<form method="post" class="flex flex-wrap gap-2 items-end">
<input type="hidden" name="task_id" value="{tid}">
<input type="hidden" name="redirect_task" value="{tid}">
<input name="note" placeholder="确认备注" class="flex-1 min-w-[120px] bg-white border border-border rounded-lg px-3 py-2 text-[13px]"/>
<button type="submit" name="action" value="ack" class="px-3 py-2 rounded-lg border border-border bg-white text-text-primary text-[13px] font-medium hover:bg-surface-hover">确认</button>
</form>
<form method="post" class="flex flex-col gap-2">
<input type="hidden" name="task_id" value="{tid}">
<input type="hidden" name="redirect_task" value="{tid}">
<div class="flex flex-wrap gap-2 items-center">
<select name="generator" class="bg-white border border-border rounded-lg px-2 py-2 text-[13px]">
<option value="local">local</option>
<option value="app-server">app-server</option>
<option value="codex">codex</option>
</select>
<label class="flex items-center gap-1 text-[13px] text-text-secondary cursor-pointer">
<input type="checkbox" name="publish" value="1" class="rounded border-border"/>发布到飞书
</label>
</div>
<button type="submit" name="action" value="retry" class="w-full px-3 py-2 rounded-lg bg-primary text-white text-[13px] font-medium hover:bg-primary-hover">重试任务</button>
</form>
</div>"""


def _read_control_timeline_lines(task_dir: Path, limit: int = 40) -> list[str]:
    path = task_dir / "control.jsonl"
    if not path.is_file():
        return []
    lines_out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            typ = str(obj.get("type") or "event")
            snippet = json.dumps(obj, ensure_ascii=False)[:220]
            lines_out.append(f"{typ}: {snippet}")
        except json.JSONDecodeError:
            lines_out.append(line[:220])
    return lines_out[-limit:]


def _timeline_panel_html(t: TaskSummary, events: EventSummary) -> str:
    ctrl = _read_control_timeline_lines(t.path)
    ev_lines = [f"事件文件: {escape(name)}" for name in events.latest_files]
    rows: list[str] = []
    for line in ctrl:
        rows.append(
            f'<li style="margin:0 0 8px;font-size:13px;color:#334155;line-height:1.5;word-break:break-all;">{escape(line)}</li>'
        )
    if not rows and not ev_lines:
        return '<p class="text-[13px] text-text-secondary">暂无控制指令与事件索引。</p>'
    parts = []
    if rows:
        parts.append(
            '<h4 style="margin:0 0 8px;font-size:12px;color:#8F959E;">control.jsonl（最近）</h4><ul style="padding-left:18px;margin:0;">'
            + "".join(rows)
            + "</ul>"
        )
    if ev_lines:
        parts.append(
            '<h4 style="margin:16px 0 8px;font-size:12px;color:#8F959E;">events 目录（最近文件）</h4><ul style="padding-left:18px;margin:0;">'
            + "".join(f"<li style=\"margin:0 0 6px;font-size:13px;\">{x}</li>" for x in ev_lines)
            + "</ul>"
        )
    return "".join(parts)


def _right_inspector_drawer(rows_html: str, artifact_list: str, ops_html: str, t: TaskSummary, events: EventSummary) -> str:
    """Match `GUI/code.html`: tab strip + single scroll stack (详情 + 工件); timeline appended for live data."""
    timeline = _timeline_panel_html(t, events)
    return f"""<div class="h-14 border-b border-border flex flex-col justify-center px-5 shrink-0">
<h2 class="text-[16px] font-semibold text-text-primary">智能体交互空间</h2>
<p class="text-[12px] text-text-secondary mt-0.5">Metadata &amp; Artifacts</p>
</div>
<div class="flex border-b border-border shrink-0 px-2" role="tablist" aria-label="Inspector">
<div class="flex-1 py-3 flex items-center justify-center gap-1.5 border-b-2 border-primary text-primary font-medium text-[14px]">
<span class="material-symbols-outlined text-[18px]">info</span><span>详情</span>
</div>
<div class="flex-1 py-3 flex items-center justify-center gap-1.5 text-text-secondary text-[14px]">
<span class="material-symbols-outlined text-[18px]">description</span><span>工件</span>
</div>
<div class="flex-1 py-3 flex items-center justify-center gap-1.5 text-text-secondary text-[14px]">
<span class="material-symbols-outlined text-[18px]">history</span><span>时间线</span>
</div>
</div>
<div class="flex-1 overflow-y-auto p-5 space-y-6 min-h-0">
<section>
<h3 class="text-[12px] font-medium text-text-secondary mb-3 border-b border-border pb-2">执行详情</h3>
<div class="space-y-3">{rows_html}</div>
{ops_html}
</section>
<section>
<h3 class="text-[12px] font-medium text-text-secondary mb-3 border-b border-border pb-2">已生成工件</h3>
<div class="space-y-2">{artifact_list}</div>
</section>
<section>
<h3 class="text-[12px] font-medium text-text-secondary mb-3 border-b border-border pb-2">时间线</h3>
{timeline}
</section>
</div>"""


def _main_header_tools(task_id: str) -> str:
    tid_q = quote(task_id, safe="")
    return f"""<div class="flex items-center gap-2 text-text-secondary">
<button type="button" class="w-8 h-8 flex items-center justify-center rounded hover:bg-surface-hover transition-colors duration-150" title="全屏" aria-label="全屏" onclick="document.documentElement.requestFullscreen&&document.documentElement.requestFullscreen()">
<span class="material-symbols-outlined text-[20px]">open_in_full</span>
</button>
<a class="w-8 h-8 flex items-center justify-center rounded hover:bg-surface-hover transition-colors" href="/?task={tid_q}" title="刷新"><span class="material-symbols-outlined text-[20px]">sync</span></a>
<details class="relative">
<summary class="w-8 h-8 flex items-center justify-center rounded hover:bg-surface-hover transition-colors cursor-pointer list-none" style="list-style:none;" title="更多">
<span class="material-symbols-outlined text-[20px]">more_horiz</span>
</summary>
<div class="absolute right-0 top-full mt-1 bg-white border border-border rounded-lg shadow-md py-2 min-w-[200px] z-50 text-[13px] text-text-primary">
<a class="block px-3 py-2 hover:bg-surface-hover no-underline text-inherit" href="/?task={tid_q}">刷新本页</a>
<p class="px-3 py-1 text-text-secondary text-[12px] m-0">任务 ID</p>
<p class="px-3 pb-2 font-mono text-[12px] break-all m-0">{escape(task_id)}</p>
</div>
</details>
</div>"""


def _shell_head(title: str) -> str:
    return f"""<!DOCTYPE html>
<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>{escape(title)}</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap" rel="stylesheet"/>
<style>
.material-symbols-outlined {{ font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24; }}
details > summary::-webkit-details-marker {{ display: none; }}
</style>
<script id="tailwind-config">
tailwind.config = {{
  darkMode: "class",
  theme: {{
    extend: {{
      colors: {{
        primary: "#3370FF",
        "primary-hover": "#2B5CD9",
        background: "#F5F6F7",
        surface: "#FFFFFF",
        "surface-hover": "#F0F2F5",
        "text-primary": "#1F2329",
        "text-secondary": "#8F959E",
        "text-tertiary": "#DEE0E3",
        border: "#DEE0E3",
        success: "#14C393",
        warning: "#FF7D00",
        error: "#F53F3F",
        "tag-bg-blue": "#E1EAFF",
        "tag-text-blue": "#3370FF",
        "tag-bg-gray": "#F0F2F5",
        "tag-text-gray": "#8F959E"
      }},
      borderRadius: {{ DEFAULT: "4px", md: "6px", lg: "8px", xl: "12px", "2xl": "16px", full: "9999px" }},
      fontFamily: {{ sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"] }}
    }}
  }}
}};
</script>
</head>"""


def render_cockpit_document(
    tasks: list[TaskSummary],
    events: EventSummary,
    flash: str,
    selected_task_id: str | None,
    search_query: str,
) -> str:
    filtered = _filter_tasks(tasks, search_query)
    selected = _pick_selected(filtered, selected_task_id)
    groups = _group_by_session(filtered)

    flash_html = ""
    if flash:
        flash_html = f"""<div class="mx-6 mt-4 rounded-lg border border-green-200 bg-[#E8F8F2] text-[#006D4B] px-4 py-3 text-[13px]">{escape(flash)}</div>"""

    sidebar_links: list[str] = []
    for session_name, group in groups.items():
        group_open = selected is not None and any(t.task_id == selected.task_id for t in group)
        items: list[str] = []
        for t in group:
            active = selected is not None and t.task_id == selected.task_id
            bar = (
                '<div class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-primary rounded-r-full"></div>'
                if active
                else ""
            )
            row_cls = (
                "flex items-center gap-3 px-3 py-2 rounded-lg text-primary bg-tag-bg-blue cursor-pointer ml-1"
                if active
                else "flex items-center gap-3 px-3 py-2 rounded-lg text-text-primary hover:bg-surface-hover transition-colors cursor-pointer ml-1"
            )
            q_suffix = f"&q={quote(search_query)}" if search_query.strip() else ""
            href = f"/?task={quote(t.task_id, safe='')}{q_suffix}"
            session_title = _session_display_title(t)
            session_menu = _session_menu_html(t, search_query)
            items.append(
                f"""<div class="relative group flex items-center">{bar}<a class="{row_cls} min-w-0 flex-1" href="{href}" data-task-id="{escape(t.task_id)}">
<span class="material-symbols-outlined text-[18px] {'text-primary' if active else 'text-text-secondary'}">chat_bubble</span>
<span class="truncate {'font-medium' if active else ''}">{escape(session_title)}</span>
</a>{session_menu}</div>"""
            )
        open_attr = " open" if group_open else ""
        sidebar_links.append(
            f"""<details class="session-group"{open_attr}>
<summary class="group flex items-center justify-between px-3 py-1.5 text-[12px] font-medium text-text-secondary cursor-pointer rounded-md hover:bg-surface-hover">
<span class="truncate">{escape(session_name)}</span>
<span class="material-symbols-outlined text-[16px] transition-transform group-open:rotate-180">expand_more</span>
</summary>
<div class="space-y-0.5 mt-1">{"".join(items)}</div>
</details>"""
        )

    if tasks and not filtered:
        sidebar_body = '<p class="px-3 text-[12px] text-text-secondary">无匹配任务，请调整搜索关键词。</p>'
    elif sidebar_links:
        sidebar_body = "".join(sidebar_links)
    else:
        sidebar_body = '<p class="px-3 text-[12px] text-text-secondary">暂无会话分组</p>'

    aside_placeholder = (
        '<div class="flex flex-col h-full"><div class="p-6 text-[13px] text-text-secondary">'
        "选择左侧任务查看详情与操作。</div></div>"
    )

    if not tasks:
        main_column = f"""{flash_html}
<div class="flex-1 flex items-center justify-center p-10">
<div class="max-w-md text-center border border-dashed border-border rounded-2xl bg-white p-10">
<h2 class="text-[18px] font-semibold text-text-primary mb-2">暂无任务</h2>
<p class="text-[14px] text-text-secondary">请先运行本地 demo，或从飞书 IM 触发任务。</p>
<p class="text-[12px] text-text-tertiary mt-4">IM 事件：{events.total}</p>
</div>
</div>"""
        inspector_column = aside_placeholder
    elif not filtered:
        main_column = f"""{flash_html}
<div class="flex-1 flex items-center justify-center p-10">
<div class="max-w-md text-center border border-dashed border-border rounded-2xl bg-white p-10">
<h2 class="text-[18px] font-semibold text-text-primary mb-2">无匹配任务</h2>
<p class="text-[14px] text-text-secondary">尝试调整搜索关键词。</p>
</div>
</div>"""
        inspector_column = aside_placeholder
    elif selected is None:
        main_column = flash_html or '<div class="p-6 text-text-secondary">无法加载任务。</div>'
        inspector_column = aside_placeholder
    else:
        t = selected
        summary = escape(t.summary or "根据群聊与指令生成办公交付物。")
        badge = f'<span class="px-2 py-0.5 rounded text-[12px] font-medium bg-tag-bg-gray text-text-secondary">{escape(_state_label_en(t.state))}</span>'
        header_title = _cockpit_header_title(t)

        checklist = "".join(
            [
                _step_row(t, "context", "读取 IM / 群聊上下文"),
                _step_row(t, "brief", "生成群聊 brief"),
                _step_row(t, "execution", "Codex 执行任务"),
                _step_row(t, "artifacts", "生成交付产物"),
                _step_row(t, "delivery", "汇总与回传"),
            ]
        )
        arts = t.artifact_outputs
        artifact_cards = "".join(_artifact_card_main(lbl, val) for lbl, val in arts) or _artifact_card_main(
            "交付产物",
            "",
        )
        err = f'<p class="text-[13px] text-error mt-2">{escape(t.error)}</p>' if t.error else ""

        rows_html = _build_inspector_primary_rows_html(t)

        artifact_list = ""
        for lbl, val in arts:
            icon, kind = _artifact_kind(lbl)
            if val and val.startswith("http"):
                artifact_list += f"""<a href="{escape(val, quote=True)}" target="_blank" rel="noopener" class="flex items-start gap-3 p-2.5 rounded-lg hover:bg-surface-hover transition-colors cursor-pointer border border-transparent no-underline text-inherit">
<div class="w-8 h-8 rounded bg-tag-bg-blue flex items-center justify-center shrink-0"><span class="material-symbols-outlined text-[18px] text-primary">{icon}</span></div>
<div><p class="text-[14px] text-text-primary font-medium leading-tight mb-1">{escape(lbl)}</p><p class="text-[12px] text-text-secondary uppercase">{escape(kind)}</p></div>
</a>"""
            else:
                artifact_list += f"""<div class="flex items-start gap-3 p-2.5 rounded-lg hover:bg-surface-hover transition-colors border border-transparent">
<div class="w-8 h-8 rounded bg-tag-bg-gray flex items-center justify-center shrink-0"><span class="material-symbols-outlined text-[18px] text-text-secondary">{icon}</span></div>
<div><p class="text-[14px] text-text-primary font-medium leading-tight mb-1">{escape(lbl)}</p><p class="text-[12px] text-text-secondary">{escape(val) or "待生成"}</p></div>
</div>"""
        if not artifact_list:
            artifact_list = '<p class="text-[13px] text-text-secondary">暂无工件链接</p>'

        main_column = f"""{flash_html}
<header class="h-14 border-b border-border bg-white flex items-center justify-between px-6 shrink-0">
<div class="flex items-center gap-3 min-w-0">
<h2 class="text-[16px] font-semibold text-text-primary truncate">{escape(header_title)}</h2>
{badge}
<span class="sr-only" data-state="{escape(t.state)}" data-task-id="{escape(t.task_id)}">state={escape(t.state)}</span>
</div>
{_main_header_tools(t.task_id)}
</header>
<div class="flex-1 overflow-y-auto p-6 space-y-6 pb-32">
<div class="flex justify-end w-full max-w-4xl mx-auto">
<div class="bg-primary text-white rounded-xl rounded-tr-sm px-4 py-3 max-w-[75%] shadow-sm">
<p class="text-[14px] leading-relaxed">{summary}</p>
</div>
</div>
<div class="flex justify-start w-full max-w-4xl mx-auto gap-3">
<div class="w-8 h-8 rounded-full bg-tag-bg-blue flex items-center justify-center shrink-0">
<span class="material-symbols-outlined text-[18px] text-primary">smart_toy</span>
</div>
<div class="space-y-3 w-full max-w-[85%]">
<div class="bg-white border border-border rounded-xl rounded-tl-sm p-4 shadow-sm">
<p class="text-[14px] text-text-primary mb-3">收到，正在为你梳理并生成相关材料，执行计划如下：</p>
<div class="space-y-2">{checklist}</div>
</div>
<div class="grid grid-cols-2 gap-3">{artifact_cards}</div>
{err}
</div>
</div>
</div>
<div class="absolute bottom-0 left-0 right-0 bg-background pt-4 pb-6 px-6 z-20">
{_append_form(t.task_id)}
</div>"""

        inspector_column = _right_inspector_drawer(
            rows_html,
            artifact_list,
            _ops_form(t.task_id),
            t,
            events,
        )

    title = "Agent-Pilot Cockpit"
    q_val = escape(search_query)

    search_form = f"""<form method="get" action="/" class="relative w-full">
<span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-text-secondary">search</span>
<input name="q" value="{q_val}" class="w-full bg-white border border-border rounded-lg pl-9 pr-3 py-1.5 text-[14px] focus:ring-1 focus:ring-primary focus:border-primary placeholder-text-secondary transition-all shadow-sm" placeholder="Search sessions..."/>
</form>"""

    return f"""{_shell_head(title)}
<body class="bg-background text-text-primary h-screen w-full flex overflow-hidden font-sans text-[14px]">
<span class="sr-only">Agent-Pilot 办公助手 · IM 事件 {events.total} · 任务 {len(tasks)}</span>
<nav class="bg-[#F5F6F7] h-screen w-64 border-r fixed left-0 top-0 border-border flex flex-col py-4 z-20">
<div class="px-5 mb-5">
<div class="flex items-center gap-3 mb-5">
<div class="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white shrink-0 shadow-sm">
<span class="material-symbols-outlined text-[20px]">flight_takeoff</span>
</div>
<div>
<h1 class="text-[16px] font-semibold text-text-primary leading-tight">Agent-Pilot</h1>
<p class="text-[12px] text-text-secondary mt-0.5">Precision Cockpit</p>
</div>
</div>
{search_form}
</div>
<div class="px-3 mb-5 space-y-1">
<button type="button" class="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-primary text-white hover:bg-primary-hover transition-colors duration-150 cursor-pointer shadow-sm font-medium" onclick="document.getElementById('im-collab-new-task').showModal()">
<span class="material-symbols-outlined text-[18px]">add</span>
<span>新建任务</span>
</button>
<a class="flex items-center gap-3 px-3 py-2 rounded-lg text-text-primary hover:bg-surface-hover transition-colors duration-150 cursor-pointer no-underline text-inherit" href="#" title="扩展能力由 Codex / MCP / lark-cli 提供；详见仓库 README">
<span class="material-symbols-outlined text-[18px] text-text-secondary">extension</span>
<span>插件</span>
</a>
<a class="flex items-center gap-3 px-3 py-2 rounded-lg text-text-primary hover:bg-surface-hover transition-colors duration-150 cursor-pointer no-underline text-inherit" href="#" title="编排由 Bridge + Codex 执行；详见 README 后续开发流程">
<span class="material-symbols-outlined text-[18px] text-text-secondary">settings_suggest</span>
<span>自动化</span>
</a>
</div>
<div class="flex-1 overflow-y-auto px-3 space-y-5">{sidebar_body}</div>
<div class="px-3 pt-3 border-t border-border space-y-0.5 mt-auto">
<a class="flex items-center gap-3 px-3 py-2 rounded-lg text-text-primary hover:bg-surface-hover transition-colors duration-150 cursor-pointer ml-1 no-underline text-inherit" href="#" title="打开仓库根目录 README.md">
<span class="material-symbols-outlined text-[18px] text-text-secondary">help</span>
<span>帮助</span>
</a>
<a class="flex items-center gap-3 px-3 py-2 rounded-lg text-text-primary hover:bg-surface-hover transition-colors duration-150 cursor-pointer ml-1 no-underline text-inherit" href="#" title="环境变量与配置见 README「环境」章节">
<span class="material-symbols-outlined text-[18px] text-text-secondary">settings</span>
<span>设置</span>
</a>
</div>
</nav>
<main class="flex-1 ml-[256px] mr-[320px] flex flex-col h-screen bg-background relative z-0">
{main_column}
</main>
<aside class="bg-white h-screen w-80 border-l border-border fixed right-0 top-0 flex flex-col z-20 shadow-sm">
{inspector_column}
</aside>
<dialog id="im-collab-new-task" style="max-width:420px;border:1px solid #DEE0E3;border-radius:12px;padding:0;">
<div style="padding:18px 20px 8px;">
<h3 style="margin:0 0 8px;font-size:16px;color:#1F2329;">新建办公任务</h3>
<p style="margin:0;font-size:14px;color:#424655;line-height:1.6;">请在 <strong>飞书群 / 单聊</strong> 中 <strong>@ 机器人</strong> 发送自然语言需求；或在终端运行：</p>
<pre style="background:#F5F6F7;border:1px solid #DEE0E3;border-radius:8px;padding:10px;font-size:12px;overflow:auto;">python scripts/run_golembot_office_task.py --message &quot;…&quot; --generator local</pre>
<p style="margin:12px 0 0;font-size:12px;color:#8F959E;">本 Web 控制台负责任务观测与追加指令，不作为任务创建入口。</p>
</div>
<form method="dialog" style="padding:0 20px 16px;display:flex;justify-content:flex-end;">
<button type="submit" style="padding:8px 16px;border-radius:8px;background:#3370FF;color:#fff;border:none;font-weight:600;cursor:pointer;">知道了</button>
</form>
</dialog>
</body></html>"""
