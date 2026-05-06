"""Server-rendered Agent-Pilot cockpit UI (aligned with GUI/code.html design tokens)."""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from html import escape
from pathlib import Path
from urllib.parse import quote

from bridge.chat_messages import read_chat_messages
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
                t.session_title or "",
                t.chat_name or "",
                t.chat_id or "",
                t.summary or "",
                t.codex_thread_id or "",
                t.state or "",
                " ".join(f"{label} {value}" for label, value in t.artifact_outputs),
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


def _parse_iso_datetime(iso: str) -> datetime | None:
    raw = (iso or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _relative_time_display(iso: str, *, now_iso: str | None = None) -> str:
    then = _parse_iso_datetime(iso)
    if then is None:
        return ""
    now = _parse_iso_datetime(now_iso) if now_iso else datetime.now(UTC)
    if now is None:
        now = datetime.now(UTC)
    seconds = max(0, int((now - then).total_seconds()))
    if seconds < 60:
        return "刚刚"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} 分钟前"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} 小时前"
    days = hours // 24
    return f"{days} 天前"


def _cockpit_header_title(t: TaskSummary) -> str:
    session_title = (t.session_title or "").strip()
    if session_title:
        return session_title[:48] + ("…" if len(session_title) > 48 else "")
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
    rows: list[tuple[str, str]] = [("创建时间", escape(_short_created_display(t.created_at)))]
    out = []
    for label, val_html in rows:
        out.append(
            f"""<div class="flex justify-between items-center text-[14px] gap-4">
<span class="text-text-secondary shrink-0">{escape(label)}</span>
<span class="flex justify-end text-right break-all min-w-0">{val_html}</span>
</div>"""
        )
    return "".join(out)


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
    q = escape(search_query, quote=True)
    return f"""<details class="relative session-actions hidden group-hover:block focus-within:block shrink-0">
<summary class="list-none w-7 h-7 rounded-md hover:bg-white/80 flex items-center justify-center cursor-pointer text-text-secondary" aria-label="会话操作" title="会话操作">
<span class="material-symbols-outlined text-[18px]">more_vert</span>
</summary>
<div class="absolute right-0 top-full mt-1 w-36 bg-white border border-border rounded-lg shadow-lg p-1.5 z-50 text-[13px]">
<label for="rename-{tid}" class="flex items-center gap-2 rounded-md px-2 py-2 text-text-primary hover:bg-surface-hover cursor-pointer">
<span class="material-symbols-outlined text-[17px] text-text-primary">edit</span><span>重命名</span>
</label>
<form method="post">
<input type="hidden" name="action" value="delete_session">
<input type="hidden" name="task_id" value="{tid}">
<input type="hidden" name="session_key" value="{session_key}">
<input type="hidden" name="redirect_task" value="{tid}">
<input type="hidden" name="q" value="{q}">
<button type="submit" class="w-full flex items-center gap-2 rounded-md px-2 py-2 text-error hover:bg-[#FFECE8] text-left">
<span class="material-symbols-outlined text-[17px] text-error">delete</span><span>删除</span>
</button>
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


def _markdown_section(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return ""
    collected: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def _task_request_message(t: TaskSummary) -> str:
    request_path = t.path / "request.md"
    if not request_path.is_file():
        return ""
    markdown = request_path.read_text(encoding="utf-8")
    section = _markdown_section(markdown, "## User Message")
    if section:
        return section
    lines = [line.strip() for line in markdown.splitlines() if line.strip() and not line.startswith(("session_key:", "chat_id:", "sender_id:"))]
    return "\n".join(lines[:8]).strip()


def _append_instruction_items(t: TaskSummary, limit: int = 8) -> list[dict[str, str]]:
    path = t.path / "control.jsonl"
    if not path.is_file():
        return []
    items: list[dict[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            command = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if command.get("type") != "append_instruction":
            continue
        payload = command.get("payload")
        if not isinstance(payload, dict):
            continue
        text = str(payload.get("text") or "").strip()
        if text:
            items.append({"text": text, "timestamp": str(command.get("timestamp") or "")})
    return items[-limit:]


def _pending_append_instruction_items(t: TaskSummary) -> list[dict[str, str]]:
    status_time = _parse_iso_datetime(t.updated_at)
    pending: list[dict[str, str]] = []
    for item in _append_instruction_items(t):
        item_time = _parse_iso_datetime(item.get("timestamp", ""))
        if t.state == "completed" and (item_time is None or status_time is None or item_time > status_time):
            pending.append(item)
    return pending


def _task_display_state(t: TaskSummary) -> str:
    if _pending_append_instruction_items(t):
        return "pending_reply"
    return t.state


def _display_state_label(state: str) -> str:
    if state == "pending_reply":
        return "待回复"
    return _state_label(state)


def _display_state_badge_html(t: TaskSummary) -> str:
    state = _task_display_state(t)
    if state == "pending_reply":
        return '<span class="px-2 py-0.5 rounded text-[12px] font-medium bg-[#FFF0E6] text-warning">待回复</span>'
    return f'<span class="px-2 py-0.5 rounded text-[12px] font-medium bg-tag-bg-gray text-text-secondary">{escape(_state_label_en(t.state))}</span>'


def _user_chat_bubble_html(text: str) -> str:
    return f"""<div data-role="chat-message-user" class="flex justify-end w-full max-w-4xl mx-auto">
<div class="bg-primary text-white rounded-xl rounded-tr-sm px-4 py-3 max-w-[75%] shadow-sm">
<p class="text-[14px] leading-relaxed whitespace-pre-wrap">{escape(text)}</p>
</div>
</div>"""


def render_user_chat_message_fragment(text: str) -> str:
    return _user_chat_bubble_html(text)


def _assistant_chat_bubble_html(text: str) -> str:
    return f"""<div data-role="chat-message-assistant" data-assistant-response="true" class="flex justify-start w-full max-w-4xl mx-auto gap-3">
<div class="w-8 h-8 rounded-full bg-tag-bg-blue flex items-center justify-center shrink-0">
<span class="material-symbols-outlined text-[18px] text-primary">smart_toy</span>
</div>
<div class="bg-white border border-border rounded-xl rounded-tl-sm px-4 py-3 shadow-sm max-w-[85%]">
<p class="text-[14px] text-text-primary whitespace-pre-wrap leading-relaxed">{escape(text)}</p>
</div>
</div>"""


def _pending_reply_marker_html() -> str:
    return """<div data-role="pending-reply-marker" class="w-full max-w-4xl mx-auto flex justify-end">
<span class="text-[12px] text-text-secondary bg-tag-bg-gray rounded-full px-3 py-1">待回复</span>
</div>"""


def render_pending_reply_marker_fragment() -> str:
    return _pending_reply_marker_html()


def _assistant_typing_bubble_html(text: str = "") -> str:
    body = (
        f'<p class="text-[14px] text-text-primary whitespace-pre-wrap leading-relaxed">{escape(text)}</p>'
        if text.strip()
        else """<div class="flex items-center gap-1.5 py-1" aria-label="assistant 正在回复">
<span class="w-2 h-2 rounded-full bg-text-secondary animate-bounce [animation-delay:-0.2s]"></span>
<span class="w-2 h-2 rounded-full bg-text-secondary animate-bounce [animation-delay:-0.1s]"></span>
<span class="w-2 h-2 rounded-full bg-text-secondary animate-bounce"></span>
</div>"""
    )
    return f"""<div data-role="chat-message-assistant-live" class="flex justify-start w-full max-w-4xl mx-auto gap-3">
<div class="w-8 h-8 rounded-full bg-tag-bg-blue flex items-center justify-center shrink-0">
<span class="material-symbols-outlined text-[18px] text-primary">smart_toy</span>
</div>
<div class="bg-white border border-border rounded-xl rounded-tl-sm p-4 shadow-sm max-w-[85%] min-w-[72px]">
{body}
</div>
</div>"""


def render_assistant_typing_fragment() -> str:
    return _assistant_typing_bubble_html()


def _render_checklist_html(t: TaskSummary) -> str:
    return "".join(
        [
            _step_row(t, "context", "读取 IM / 群聊上下文"),
            _step_row(t, "brief", "生成群聊 brief"),
            _step_row(t, "execution", "Codex 执行任务"),
            _step_row(t, "artifacts", "生成交付产物"),
            _step_row(t, "delivery", "汇总与回传"),
        ]
    )


def render_assistant_bubble_fragment(t: TaskSummary) -> str:
    messages = [message for message in _chat_log_messages(t) if message[1] == "assistant"]
    return _assistant_chat_bubble_html(messages[-1][2]) if messages else ""


def _chat_transcript_html(t: TaskSummary) -> str:
    messages: list[tuple[datetime, int, str]] = []
    for timestamp, role, text in _chat_log_messages(t):
        order = 0 if role == "user" else 1
        html = _user_chat_bubble_html(text) if role == "user" else _assistant_chat_bubble_html(text)
        messages.append((timestamp, order, html))
    messages.sort(key=lambda item: (item[0], item[1]))
    rendered = "".join(item[2] for item in messages)
    live_text = _codex_stream_text(t)
    if _should_show_live_assistant(t):
        rendered += _assistant_typing_bubble_html(live_text)
    if _pending_append_instruction_items(t):
        rendered += _pending_reply_marker_html()
    if not rendered:
        rendered = _user_chat_bubble_html(_task_request_message(t) or "你好")
    return rendered


def _chat_log_messages(t: TaskSummary) -> list[tuple[datetime, str, str]]:
    stored = read_chat_messages(t.path)
    if stored:
        out: list[tuple[datetime, str, str]] = []
        for message in stored:
            timestamp = _parse_iso_datetime(str(message.get("timestamp") or "")) or datetime.max.replace(tzinfo=UTC)
            out.append((timestamp, str(message["role"]), str(message["text"])))
        return out

    out = []
    request = _task_request_message(t)
    if request:
        created = _parse_iso_datetime(t.created_at) or datetime.min.replace(tzinfo=UTC)
        out.append((created, "user", request))
    if t.summary:
        out.append((_assistant_message_time(t), "assistant", t.summary))
    for item in _append_instruction_items(t):
        ts = _parse_iso_datetime(item.get("timestamp", "")) or datetime.max.replace(tzinfo=UTC)
        out.append((ts, "user", item["text"]))
    return out


def _assistant_message_time(t: TaskSummary) -> datetime:
    created = _parse_iso_datetime(t.created_at) or datetime.min.replace(tzinfo=UTC)
    if t.summary:
        artifact_time = _artifact_protocol_time(t)
        if artifact_time is not None:
            return max(artifact_time, created + timedelta(microseconds=1))
    if t.state == "failed" and t.summary:
        return created + timedelta(microseconds=1)
    return _parse_iso_datetime(t.updated_at) or datetime.max.replace(tzinfo=UTC)


def _artifact_protocol_time(t: TaskSummary) -> datetime | None:
    path = t.path / "artifacts.json"
    if not path.is_file():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)


def _should_show_live_assistant(t: TaskSummary) -> bool:
    if t.state not in {"running", "failed"}:
        return False
    appends = _append_instruction_items(t)
    chat_messages = _chat_log_messages(t)
    if not appends and not chat_messages:
        return False
    assistant_time = _assistant_message_time(t)
    has_new_append = False
    for item in appends:
        item_time = _parse_iso_datetime(item.get("timestamp", ""))
        if item_time is None or item_time > assistant_time:
            has_new_append = True
            break
    if not has_new_append:
        for item_time, role, _text in chat_messages:
            if role == "user" and item_time > assistant_time:
                has_new_append = True
                break
    if not has_new_append:
        return bool(t.state == "running" and _codex_stream_text(t).strip())
    return t.state == "running" or bool(_codex_stream_text(t).strip())


def _codex_stream_text(t: TaskSummary) -> str:
    path = t.path / "codex-stream.jsonl"
    if not path.is_file():
        return ""
    chunks: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        text = str(event.get("text") or "").strip()
        if text and _is_user_facing_stream_text(text):
            chunks.append(text)
    return "\n".join(_dedupe_preserve_order(chunks[-8:])).strip()


def _is_user_facing_stream_text(text: str) -> bool:
    value = text.strip()
    if not value:
        return False
    if len(value) < 4 and value.lower() != "ok":
        return False
    if value.startswith(("{", "[", "}", "]")):
        return False
    if "Under-development features enabled" in value:
        return False
    if "Success. Updated the following files" in value:
        return False
    if re.search(r"(^|\s)(/[^ \n]+|[A-Za-z]:\\[^ \n]+)", value):
        return False
    if re.search(r"\b(plan|artifacts|status|control|request|reply)\.json\b", value):
        return False
    if re.search(r"\b(reply|document|slides|whiteboard)\.(md|mmd|json)\b", value):
        return False
    if value.count("{") + value.count("}") + value.count('"') >= 4:
        return False
    return True


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def render_task_chat_fragment(t: TaskSummary) -> str:
    return _chat_transcript_html(t)


def _workspace_status_message(t: TaskSummary) -> str:
    artifact_count = len(t.artifact_outputs)
    pending_count = len(_pending_append_instruction_items(t))
    if pending_count:
        return f"已记录 {pending_count} 条后续补充。当前工件尚未根据这些补充更新。"
    if t.state == "completed":
        if artifact_count:
            return f"已完成当前任务，生成 {artifact_count} 个工件。"
        return "已完成当前任务。"
    if t.state == "failed":
        return "任务执行失败，错误信息见下方详情面板。"
    if t.state == "waiting_for_user":
        return "我需要补充确认后再继续，确认项和控制记录见右侧详情。"
    if t.state == "running":
        return "正在处理当前任务；新的补充会通过同一控制通道追加给执行后端。"
    return "已收到当前任务，等待执行后会持续同步状态。"


def _append_form(task_id: str) -> str:
    tid = escape(task_id)
    stream_url = escape(f"/api/task-stream?task={quote(task_id, safe='')}", quote=True)
    return f"""<form method="post" data-async-append="true" data-stream-url="{stream_url}" class="max-w-4xl mx-auto bg-white border border-border rounded-xl shadow-sm focus-within:ring-1 focus-within:ring-primary focus-within:border-primary transition-all flex items-end p-2 gap-2">
<input type="hidden" name="action" value="append">
<input type="hidden" name="task_id" value="{tid}">
<input type="hidden" name="redirect_task" value="{tid}">
<label class="p-2 text-text-secondary shrink-0 cursor-not-allowed opacity-70" title="附件请通过飞书会话发送">
<input type="file" class="hidden" disabled tabindex="-1"/>
<span class="material-symbols-outlined text-[20px]">attach_file</span>
</label>
<textarea name="text" required rows="1" data-submit-on-enter="true" placeholder="添加指令..." class="w-full bg-transparent border-none resize-none focus:ring-0 text-[14px] py-2 px-2 max-h-32 placeholder-text-secondary text-text-primary outline-none"></textarea>
<button type="submit" class="w-9 h-9 rounded-lg bg-primary text-white hover:bg-primary-hover flex items-center justify-center transition-colors shrink-0 mb-0.5 mr-0.5" title="发送">
<span class="material-symbols-outlined text-[18px]">send</span>
</button>
</form>"""


def _retry_form(task_id: str, label: str) -> str:
    tid = escape(task_id)
    return f"""<form method="post">
<input type="hidden" name="task_id" value="{tid}">
<input type="hidden" name="redirect_task" value="{tid}">
<input type="hidden" name="generator" value="app-server">
<button type="submit" name="action" value="retry" class="w-full px-3 py-2 rounded-lg bg-primary text-white text-[13px] font-medium hover:bg-primary-hover">{escape(label)}</button>
</form>"""


def _ops_form(t: TaskSummary) -> str:
    tid = escape(t.task_id)
    display_state = _task_display_state(t)
    if display_state == "pending_reply":
        return f"""<div class="space-y-3 pt-2 border-t border-border">
{_retry_form(t.task_id, "执行补充")}
</div>"""
    if t.state in {"completed", "failed"}:
        return f"""<div class="space-y-3 pt-2 border-t border-border">
{_retry_form(t.task_id, "重新执行")}
</div>"""
    if t.state == "waiting_for_user":
        return f"""<div class="space-y-3 pt-2 border-t border-border">
<form method="post" class="flex flex-wrap gap-2 items-end">
<input type="hidden" name="task_id" value="{tid}">
<input type="hidden" name="redirect_task" value="{tid}">
<input name="note" placeholder="确认备注" class="flex-1 min-w-[120px] bg-white border border-border rounded-lg px-3 py-2 text-[13px]"/>
<button type="submit" name="action" value="ack" class="px-3 py-2 rounded-lg border border-border bg-white text-text-primary text-[13px] font-medium hover:bg-surface-hover">确认</button>
</form>
{_retry_form(t.task_id, "重新执行")}
</div>"""
    return f"""<div class="space-y-3 pt-2 border-t border-border">
<form method="post" class="flex flex-wrap gap-2 items-center">
<input type="hidden" name="task_id" value="{tid}">
<input type="hidden" name="redirect_task" value="{tid}">
<button type="submit" name="action" value="interrupt" class="px-3 py-2 rounded-lg bg-[#FFECE8] text-error text-[13px] font-medium hover:opacity-90">打断</button>
</form>
{_retry_form(t.task_id, "重新执行")}
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


def _session_artifact_outputs(tasks: list[TaskSummary], selected: TaskSummary) -> list[tuple[str, str]]:
    selected_group = _task_group_label(selected)
    outputs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for task in tasks:
        if _task_group_label(task) != selected_group:
            continue
        for label, value in task.artifact_outputs:
            key = (label, value)
            if key in seen:
                continue
            seen.add(key)
            outputs.append(key)
    return outputs


def _right_inspector_drawer(rows_html: str, artifact_list: str) -> str:
    return f"""<div class="h-14 border-b border-border flex flex-col justify-center px-5 shrink-0">
<h2 class="text-[16px] font-semibold text-text-primary">智能体交互空间</h2>
<p class="text-[12px] text-text-secondary mt-0.5">Metadata &amp; Artifacts</p>
</div>
<div class="flex-1 overflow-y-auto p-5 space-y-6 min-h-0">
<section>
<h3 class="text-[12px] font-medium text-text-secondary mb-3 border-b border-border pb-2">执行详情</h3>
<div class="space-y-3">{rows_html}</div>
</section>
<section>
<h3 class="text-[12px] font-medium text-text-secondary mb-3 border-b border-border pb-2">已生成工件</h3>
<div class="space-y-2">{artifact_list}</div>
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
.session-rename-toggle:checked ~ .session-link {{ display: none; }}
.session-rename-toggle:checked ~ .session-rename-inline {{ display: flex; }}
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
<script>
document.addEventListener("DOMContentLoaded", () => {{
  const scrollChatToBottom = () => {{
    const chat = document.querySelector("[data-chat-scroll-container='true']");
    if (chat) chat.scrollTop = chat.scrollHeight;
  }};
  scrollChatToBottom();
  const storageKey = "im-collab-cockpit-open-groups";
  let saved = null;
  try {{ saved = JSON.parse(localStorage.getItem(storageKey) || "null"); }} catch (_err) {{ saved = null; }}
  const details = Array.from(document.querySelectorAll("[data-session-group]"));
  if (saved && typeof saved === "object") {{
    for (const detail of details) {{
      const key = detail.getAttribute("data-session-group") || "";
      detail.open = Boolean(saved[key]);
    }}
  }}
  const persist = () => {{
    const next = {{}};
    for (const detail of details) {{
      next[detail.getAttribute("data-session-group") || ""] = detail.open;
    }}
    localStorage.setItem(storageKey, JSON.stringify(next));
  }};
 for (const detail of details) detail.addEventListener("toggle", persist);
  for (const toggle of document.querySelectorAll(".session-rename-toggle")) {{
    toggle.addEventListener("change", () => {{
      if (!toggle.checked) return;
      const row = toggle.closest(".group");
      const input = row ? row.querySelector(".session-rename-inline input[name='session_title']") : null;
      if (input) {{
        setTimeout(() => {{
          input.focus();
          input.select();
        }}, 0);
      }}
    }});
  }}
  for (const textarea of document.querySelectorAll("textarea[data-submit-on-enter='true']")) {{
    textarea.addEventListener("keydown", (event) => {{
      if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
      event.preventDefault();
      const form = textarea.closest("form");
      if (form) form.requestSubmit();
    }});
  }}
  let taskStream = null;
  let _lastAssistantHtml = "";
  const _pendingMarkerHtml = '<div data-role="pending-reply-marker" class="w-full max-w-4xl mx-auto flex justify-end"><span class="text-[12px] text-text-secondary bg-tag-bg-gray rounded-full px-3 py-1">待回复</span></div>';
  const openTaskStream = (url) => {{
    if (!url || typeof EventSource === "undefined") return;
    if (taskStream) taskStream.close();
    taskStream = new EventSource(url);
    taskStream.onmessage = (event) => {{
      const data = JSON.parse(event.data);
      const chat = document.querySelector("[data-chat-scroll-container='true']");
      if (!chat) return;
      if (data.chat_html !== undefined) {{
        if (data.chat_html && chat.innerHTML !== data.chat_html) {{
          chat.innerHTML = data.chat_html;
          _lastAssistantHtml = data.assistant_html || "";
        }}
        scrollChatToBottom();
        if (data.done && taskStream) {{
          taskStream.close();
          taskStream = null;
        }}
        return;
      }}
      // Fallback for older stream payloads: update assistant response block only when its content changes.
      if (data.assistant_html !== undefined) {{
        const currentAssistant = chat.querySelector("[data-assistant-response='true']");
        if (data.assistant_html !== _lastAssistantHtml) {{
          if (currentAssistant) {{
            if (data.assistant_html) {{
              currentAssistant.outerHTML = data.assistant_html;
            }} else {{
              currentAssistant.remove();
            }}
          }} else if (data.assistant_html) {{
            const marker = chat.querySelector("[data-role='pending-reply-marker']");
            if (marker) {{
              marker.insertAdjacentHTML("beforebegin", data.assistant_html);
            }} else {{
              chat.insertAdjacentHTML("beforeend", data.assistant_html);
            }}
          }}
          _lastAssistantHtml = data.assistant_html;
        }}
      }}
      // Update pending reply marker based on control status
      if (data.pending_controls !== undefined) {{
        const marker = chat.querySelector("[data-role='pending-reply-marker']");
        if (data.pending_controls) {{
          if (!marker) chat.insertAdjacentHTML("beforeend", _pendingMarkerHtml);
        }} else {{
          if (marker) marker.remove();
        }}
      }}
      scrollChatToBottom();
      if (data.done && taskStream) {{
        taskStream.close();
        taskStream = null;
      }}
    }};
    taskStream.onerror = () => {{
      if (taskStream) taskStream.close();
      taskStream = null;
    }};
  }};
  for (const form of document.querySelectorAll("form[data-async-append='true']")) {{
    form.addEventListener("submit", async (event) => {{
      event.preventDefault();
      const textarea = form.querySelector("textarea[name='text']");
      const text = textarea ? textarea.value.trim() : "";
      if (!text) return;
      const button = form.querySelector("button[type='submit']");
      if (button) button.disabled = true;
      try {{
        const response = await fetch(form.action || window.location.href, {{
          method: "POST",
          headers: {{"Accept": "application/json"}},
          body: new URLSearchParams(new FormData(form)),
        }});
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || "send failed");
        const chat = document.querySelector("[data-chat-scroll-container='true']");
        if (chat) {{
          for (const node of chat.querySelectorAll("[data-role='pending-reply-marker']")) node.remove();
          for (const node of chat.querySelectorAll("[data-role='chat-message-assistant-live']")) node.remove();
          chat.insertAdjacentHTML("beforeend", data.message_html || "");
          if (data.typing_html) {{
            chat.insertAdjacentHTML("beforeend", data.typing_html);
          }} else if (data.pending_marker_html) {{
            chat.insertAdjacentHTML("beforeend", data.pending_marker_html);
          }}
          scrollChatToBottom();
        }}
        if (textarea) textarea.value = "";
        openTaskStream(data.stream_url);
      }} finally {{
        if (button) button.disabled = false;
        if (textarea) textarea.focus();
      }}
    }});
  }}
}});
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
            row_wrap_cls = (
                "relative group flex items-center rounded-lg bg-tag-bg-blue text-primary"
                if active
                else "relative group flex items-center rounded-lg text-text-primary hover:bg-surface-hover transition-colors"
            )
            link_cls = (
                "session-link flex items-center gap-2 px-3 py-2 text-primary cursor-pointer min-w-0 flex-1 no-underline"
                if active
                else "session-link flex items-center gap-2 px-3 py-2 text-text-primary cursor-pointer min-w-0 flex-1 no-underline"
            )
            q_suffix = f"&q={quote(search_query)}" if search_query.strip() else ""
            href = f"/?task={quote(t.task_id, safe='')}{q_suffix}"
            session_title = _session_display_title(t)
            session_menu = _session_menu_html(t, search_query)
            rename_id = f"rename-{escape(t.task_id)}"
            tid = escape(t.task_id)
            session_key = escape(t.session_key or "")
            title_value = escape(session_title, quote=True)
            q_value = escape(search_query, quote=True)
            relative_time = _relative_time_display(t.updated_at or t.created_at)
            status_indicator = (
                '<span class="session-active-dot w-2 h-2 rounded-full bg-primary shrink-0 mr-2 '
                'group-hover:hidden group-focus-within:hidden" aria-label="当前会话"></span>'
                if active
                else (
                    f'<span class="session-time shrink-0 mr-2 text-[12px] text-text-secondary tabular-nums '
                    f'group-hover:hidden group-focus-within:hidden">{escape(relative_time)}</span>'
                    if relative_time
                    else ""
                )
            )
            items.append(
                f"""<div class="{row_wrap_cls}">
<input id="{rename_id}" class="session-rename-toggle hidden" type="checkbox">
<a class="{link_cls}" href="{href}" data-task-id="{escape(t.task_id)}">
<span class="truncate {'font-medium' if active else ''}">{escape(session_title)}</span>
</a>
<form method="post" class="session-rename-inline hidden items-center gap-1 min-w-0 flex-1 px-2 py-1.5">
<input type="hidden" name="action" value="rename_session">
<input type="hidden" name="task_id" value="{tid}">
<input type="hidden" name="session_key" value="{session_key}">
<input type="hidden" name="redirect_task" value="{tid}">
<input type="hidden" name="q" value="{q_value}">
<input name="session_title" value="{title_value}" required autofocus onblur="this.form.requestSubmit()" class="min-w-0 flex-1 rounded-md border border-primary bg-white px-2 py-1 text-[13px] text-text-primary">
</form>
{status_indicator}
{session_menu}</div>"""
            )
        open_attr = " open" if group_open else ""
        group_key = escape(session_name, quote=True)
        sidebar_links.append(
            f"""<details class="session-group"{open_attr} data-session-group="{group_key}">
<summary class="group flex items-center justify-between px-3 py-1.5 text-[14px] font-medium text-text-primary cursor-pointer rounded-md hover:bg-surface-hover">
<span class="min-w-0 flex items-center gap-2">
<span class="material-symbols-outlined text-[20px] text-text-primary">group</span>
<span class="truncate">{escape(session_name)}</span>
</span>
<span class="material-symbols-outlined text-[16px] transition-transform group-open:rotate-180">expand_more</span>
</summary>
<div class="ml-[22px] mt-1 border-l border-border pl-4 space-y-0.5">{"".join(items)}</div>
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
<p class="text-[14px] text-text-secondary">请先从飞书会话触发任务。</p>
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
        badge = _display_state_badge_html(t)
        header_title = _cockpit_header_title(t)

        arts = t.artifact_outputs
        chat_transcript = _chat_transcript_html(t)

        rows_html = _build_inspector_primary_rows_html(t)

        artifact_list = ""
        for lbl, val in _session_artifact_outputs(tasks, t):
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
</header>
<div class="flex-1 overflow-y-auto p-6 space-y-6 pb-32" data-chat-scroll-container="true">
{chat_transcript}
</div>
<div class="absolute bottom-0 left-0 right-0 bg-background pt-4 pb-6 px-6 z-20">
{_append_form(t.task_id)}
</div>"""

        inspector_column = _right_inspector_drawer(rows_html, artifact_list)

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
</div>
<div class="flex-1 overflow-y-auto px-3">
<div class="px-3 pb-2 text-[12px] font-medium text-text-secondary">任务</div>
<div class="space-y-5">{sidebar_body}</div>
</div>
<div class="px-3 pt-3 border-t border-border space-y-0.5 mt-auto"></div>
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
<p style="margin:0;font-size:14px;color:#424655;line-height:1.6;">请在 <strong>飞书群 / 单聊</strong> 中 <strong>@ 机器人</strong> 发送自然语言需求。任务开始后，这里会同步展示进度、工件和后续指令。</p>
</div>
<form method="dialog" style="padding:0 20px 16px;display:flex;justify-content:flex-end;">
<button type="submit" style="padding:8px 16px;border-radius:8px;background:#3370FF;color:#fff;border:none;font-weight:600;cursor:pointer;">关闭</button>
</form>
</dialog>
</body></html>"""
