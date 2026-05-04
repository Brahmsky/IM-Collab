"""Server-rendered Agent-Pilot cockpit UI (aligned with GUI/code.html design tokens)."""

from __future__ import annotations

from collections import OrderedDict
from html import escape
from typing import Any
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


def _state_badge_class(state: str) -> str:
    return {
        "queued": "bg-tag-bg-gray text-text-secondary",
        "running": "bg-tag-bg-blue text-primary",
        "waiting_for_user": "bg-[#FFF0E6] text-[#FA6400]",
        "completed": "bg-[#E8F8F2] text-success",
        "failed": "bg-[#FFECE8] text-error",
    }.get(state, "bg-tag-bg-gray text-text-secondary")


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


def _group_by_session(tasks: list[TaskSummary]) -> OrderedDict[str, list[TaskSummary]]:
    groups: OrderedDict[str, list[TaskSummary]] = OrderedDict()
    for t in tasks:
        key = (t.session_key or "").strip() or "未绑定会话"
        groups.setdefault(key, []).append(t)
    return groups


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
<span class="material-symbols-outlined text-[20px] text-text-secondary shrink-0 p-2">edit_note</span>
<input name="text" required placeholder="添加指令…" class="w-full bg-transparent border-none text-[14px] py-2 px-2 placeholder-text-secondary text-text-primary outline-none"/>
<button type="submit" class="w-9 h-9 rounded-lg bg-primary text-white hover:bg-primary-hover flex items-center justify-center transition-colors shrink-0" title="发送">
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


def _shell_head(title: str) -> str:
    return f"""<!DOCTYPE html>
<html class="light" lang="zh-CN"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{escape(title)}</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap" rel="stylesheet"/>
<style>
.material-symbols-outlined {{ font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24; }}
</style>
<script>
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
      fontFamily: {{ sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"] }}
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
            items.append(
                f"""<div class="relative group">{bar}<a class="{row_cls}" href="{href}" data-task-id="{escape(t.task_id)}">
<span class="material-symbols-outlined text-[18px] {'text-primary' if active else 'text-text-secondary'}">chat_bubble</span>
<span class="truncate {'font-medium' if active else ''}">{escape(t.task_id)}</span>
</a></div>"""
            )
        sidebar_links.append(
            f"""<div>
<h3 class="px-3 text-[12px] font-medium text-text-secondary mb-1.5">{escape(session_name)}</h3>
<div class="space-y-0.5">{"".join(items)}</div>
</div>"""
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
        badge_cls = _state_badge_class(t.state)
        badge = f'<span class="px-2 py-0.5 rounded text-[12px] font-medium {badge_cls}">{escape(_state_label(t.state))}</span>'
        header_title = t.task_id[:48] + ("…" if len(t.task_id) > 48 else "")

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

        rows_html = ""
        for label, val in [
            ("状态", _state_label(t.state)),
            ("任务 ID", t.task_id),
            ("会话", t.session_key or "—"),
            ("Codex 线程", t.codex_thread_id or "—"),
            ("活跃回合", t.active_turn_id or "—"),
            ("控制队列", str(t.control_count) if t.control_count else "—"),
            ("最新操作", t.last_control_type or "—"),
            ("确认人", t.ack_operator or "—"),
            ("更新时间", t.updated_at or "—"),
        ]:
            rows_html += f"""<div class="flex justify-between items-center text-[14px] gap-4">
<span class="text-text-secondary shrink-0">{escape(label)}</span>
<span class="text-text-primary font-medium text-right break-all">{escape(val)}</span>
</div>"""

        artifact_list = ""
        for lbl, val in arts:
            icon, kind = _artifact_kind(lbl)
            if val and val.startswith("http"):
                artifact_list += f"""<a href="{escape(val, quote=True)}" target="_blank" rel="noopener" class="flex items-start gap-3 p-2.5 rounded-lg hover:bg-surface-hover border border-transparent no-underline text-inherit">
<div class="w-8 h-8 rounded bg-tag-bg-blue flex items-center justify-center shrink-0"><span class="material-symbols-outlined text-[18px] text-primary">{icon}</span></div>
<div><p class="text-[14px] text-text-primary font-medium leading-tight mb-1">{escape(lbl)}</p><p class="text-[12px] text-text-secondary uppercase">{escape(kind)}</p></div>
</a>"""
            else:
                artifact_list += f"""<div class="flex items-start gap-3 p-2.5 rounded-lg border border-transparent">
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
<div class="flex items-center gap-1 text-text-secondary">
<a class="w-8 h-8 flex items-center justify-center rounded hover:bg-surface-hover" href="/?task={quote(t.task_id, safe='')}" title="刷新"><span class="material-symbols-outlined text-[20px]">sync</span></a>
</div>
</header>
<div class="flex-1 overflow-y-auto p-6 space-y-6 pb-36">
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
<p class="text-[14px] text-text-primary mb-3">已接收上下文，执行阶段如下（状态：<span class="font-medium">{escape(t.state)}</span>）。</p>
<div class="space-y-2">{checklist}</div>
</div>
<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">{artifact_cards}</div>
{err}
</div>
</div>
</div>
<div class="absolute bottom-0 left-0 right-0 bg-background pt-3 pb-5 px-6 z-20 border-t border-border/60">
{_append_form(t.task_id)}
</div>"""

        inspector_column = f"""<div class="h-14 border-b border-border flex flex-col justify-center px-5 shrink-0">
<h2 class="text-[16px] font-semibold text-text-primary">任务详情</h2>
<p class="text-[12px] text-text-secondary mt-0.5">Metadata &amp; 操作</p>
</div>
<div class="flex-1 overflow-y-auto p-5 space-y-6">
<section>
<h3 class="text-[12px] font-medium text-text-secondary mb-3 border-b border-border pb-2">执行详情</h3>
<div class="space-y-3">{rows_html}</div>
</section>
<section>
<h3 class="text-[12px] font-medium text-text-secondary mb-3 border-b border-border pb-2">已生成工件</h3>
<div class="space-y-2">{artifact_list}</div>
</section>
{_ops_form(t.task_id)}
</div>"""

    title = "Agent-Pilot 工作台"
    q_val = escape(search_query)

    search_form = f"""<form method="get" action="/" class="relative w-full">
<span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-text-secondary">search</span>
<input name="q" value="{q_val}" class="w-full bg-white border border-border rounded-lg pl-9 pr-3 py-1.5 text-[14px] focus:ring-1 focus:ring-primary focus:border-primary placeholder-text-secondary shadow-sm" placeholder="搜索任务 / 会话…"/>
</form>"""

    overview = f"IM 事件 {events.total} · 任务 {len(tasks)}"

    return f"""{_shell_head(title)}
<body class="bg-background text-text-primary h-screen w-full flex overflow-hidden font-sans text-[14px]">
<nav class="bg-[#F5F6F7] h-screen w-64 border-r fixed left-0 top-0 border-border flex flex-col py-4 z-20">
<div class="px-5 mb-4">
<div class="flex items-center gap-3 mb-4">
<div class="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white shrink-0 shadow-sm">
<span class="material-symbols-outlined text-[20px]">flight_takeoff</span>
</div>
<div>
<h1 class="text-[16px] font-semibold text-text-primary leading-tight">Agent-Pilot</h1>
<p class="text-[12px] text-text-secondary mt-0.5">办公 cockpit</p>
</div>
</div>
<p class="text-[11px] text-text-secondary mb-2">{escape(overview)}</p>
{search_form}
</div>
<div class="px-3 mb-3">
<p class="text-[11px] font-medium text-text-secondary px-2 mb-1">Agent-Pilot 办公助手</p>
<span class="block w-full text-center px-3 py-2 rounded-lg border border-dashed border-border text-text-secondary text-[12px]">新建任务：飞书 @bot 或 <span class="font-mono">run_golembot_office_task</span></span>
</div>
<div class="flex-1 overflow-y-auto px-3 space-y-5">{sidebar_body}</div>
<div class="px-3 pt-3 border-t border-border text-[11px] text-text-secondary">静态参考：<span class="font-mono">GUI/code.html</span></div>
</nav>
<main class="flex-1 ml-[256px] mr-[320px] flex flex-col h-screen bg-background relative z-0">
{main_column}
</main>
<aside class="bg-white h-screen w-80 border-l border-border fixed right-0 top-0 flex flex-col z-20 shadow-sm">
{inspector_column}
</aside>
</body></html>"""
