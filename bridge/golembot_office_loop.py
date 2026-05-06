from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bridge.codex_app_server_task_runner import AppServerTaskBackend, run_codex_app_server_task
from bridge.codex_task_runner import run_codex_task
from bridge.feishu_delivery import publish_task_artifacts_to_feishu
from bridge.group_briefing import brief_needs_confirmation, build_confirmation_card, build_group_brief, build_group_brief_from_evidence
from bridge.group_briefing import render_confirmation_markdown, render_group_brief_markdown
from bridge.group_briefing_extractors.langextract_deepseek import DEFAULT_BASE_URL, DEFAULT_MODEL_ID, extract_evidence
from bridge.group_context_selector import select_briefing_context
from bridge.lark_im import build_delivery_markdown
from bridge.local_codex_smoke import run_local_smoke
from bridge.task_binding import bind_active_task, clear_active_task, get_task_binding
from bridge.task_control import read_control_commands
from bridge.task_protocol import create_task, read_artifacts, write_status


def run_golembot_office_task(
    message: str,
    session_key: str,
    chat_id: str,
    sender_id: str,
    tasks_root: Path,
    chat_name: str = "",
    task_id: str | None = None,
    generator: str = "local",
    publish: bool = False,
    runner: Any | None = None,
    conversation_context: list[dict[str, Any]] | None = None,
    codex_backend: AppServerTaskBackend | None = None,
    brief_extractor: str = "langextract-deepseek",
    brief_api_key: str | None = None,
    evidence_extractor: Any | None = None,
    absorbed_message_id: str | None = None,
) -> dict[str, Any]:
    task_id = task_id or _task_id_from_session(session_key)
    task_dir = tasks_root / task_id
    bindings_path = tasks_root / "task-bindings.json"

    if not task_dir.exists():
        task_dir = create_task(
            tasks_root,
            task_id,
            _request_markdown(message, session_key, chat_id, sender_id, conversation_context=conversation_context),
        )
        brief = _write_group_brief(
            task_dir,
            chat_id,
            conversation_context or [],
            brief_extractor=brief_extractor,
            brief_api_key=brief_api_key,
            evidence_extractor=evidence_extractor,
        )
    else:
        brief = None
        _append_confirmation_controls_to_request(task_dir)

    binding = bind_active_task(
        bindings_path,
        session_key=session_key,
        task_id=task_id,
        chat_id=chat_id,
        channel_type=session_key.split(":", 1)[0],
        sender_id=sender_id,
        chat_name=chat_name or None,
    )

    if brief is not None and brief_needs_confirmation(brief):
        reply_markdown = render_confirmation_markdown(brief)
        (task_dir / "confirmation.md").write_text(reply_markdown, encoding="utf-8")
        (task_dir / "confirmation_card.json").write_text(
            _json_dumps(build_confirmation_card(brief, task_id=task_id, session_key=session_key)),
            encoding="utf-8",
        )
        if absorbed_message_id is not None:
            bind_active_task(
                bindings_path,
                session_key=session_key,
                task_id=task_id,
                chat_id=chat_id,
                channel_type=session_key.split(":", 1)[0],
                sender_id=sender_id,
                chat_name=chat_name or None,
                last_absorbed_message_id=absorbed_message_id,
            )
        write_status(task_dir, "waiting_for_user", error="群聊旁批汇总发现冲突或待确认问题，需要确认后再生成。")
        return {
            "task_id": task_id,
            "task_dir": task_dir.as_posix(),
            "session_key": session_key,
            "state": "waiting_for_user",
            "reply_markdown": reply_markdown,
        }

    try:
        if _should_generate_artifacts(task_dir):
            codex_turn = _generate_artifacts(
                task_dir,
                generator,
                codex_backend=codex_backend,
                codex_thread_id=binding.get("codex_thread_id"),
                on_turn_started=lambda turn: bind_active_task(
                    bindings_path,
                    session_key=session_key,
                    task_id=task_id,
                    chat_id=chat_id,
                    channel_type=session_key.split(":", 1)[0],
                    sender_id=sender_id,
                    chat_name=chat_name or None,
                    codex_thread_id=turn.thread_id,
                    active_turn_id=turn.turn_id,
                    last_absorbed_message_id=absorbed_message_id,
                ),
            )
            if codex_turn is not None:
                bind_active_task(
                    bindings_path,
                    session_key=session_key,
                    task_id=task_id,
                    chat_id=chat_id,
                    channel_type=session_key.split(":", 1)[0],
                    sender_id=sender_id,
                    chat_name=chat_name or None,
                    codex_thread_id=codex_turn.thread_id,
                    active_turn_id=codex_turn.turn_id,
                    last_absorbed_message_id=absorbed_message_id,
                )
        if publish:
            publish_task_artifacts_to_feishu(task_dir, runner=runner)
        artifacts = read_artifacts(task_dir)
    except Exception as exc:
        write_status(task_dir, "failed", error=f"GolemBot office loop failed: {exc}")
        try:
            clear_active_task(bindings_path, session_key)
        except Exception:
            pass
        raise

    if absorbed_message_id is not None:
        current_binding = get_task_binding(bindings_path, session_key) or binding
        bind_active_task(
            bindings_path,
            session_key=session_key,
            task_id=task_id,
            chat_id=chat_id,
            channel_type=session_key.split(":", 1)[0],
            sender_id=sender_id,
            chat_name=chat_name or None,
            codex_thread_id=current_binding.get("codex_thread_id"),
            active_turn_id=current_binding.get("active_turn_id"),
            last_absorbed_message_id=absorbed_message_id,
        )
    clear_active_task(bindings_path, session_key)
    return {
        "task_id": task_id,
        "task_dir": task_dir.as_posix(),
        "session_key": session_key,
        "artifacts": artifacts,
        "reply_markdown": build_delivery_markdown(artifacts),
    }


def _generate_artifacts(
    task_dir: Path,
    generator: str,
    codex_backend: AppServerTaskBackend | None = None,
    codex_thread_id: str | None = None,
    on_turn_started: Any | None = None,
) -> Any | None:
    if generator == "local":
        run_local_smoke(task_dir)
        return None
    if generator == "codex":
        run_codex_task(task_dir, project_root=Path(__file__).resolve().parents[1])
        return None
    if generator == "app-server":
        return run_codex_app_server_task(
            task_dir,
            project_root=Path(__file__).resolve().parents[1],
            backend=codex_backend,
            thread_id=codex_thread_id,
            on_turn_started=on_turn_started,
        )
    raise ValueError(f"unsupported generator: {generator}")


def _should_generate_artifacts(task_dir: Path) -> bool:
    if not (task_dir / "artifacts.json").exists():
        return True
    try:
        status = read_status(task_dir)
    except Exception:
        return True
    status_time = _parse_iso_datetime(str(status.get("updated_at") or ""))
    if status_time is None:
        return False
    for command in read_control_commands(task_dir):
        if command.get("type") not in {"append_instruction", "confirm_instruction", "card_action"}:
            continue
        command_time = _parse_iso_datetime(str(command.get("timestamp") or ""))
        if command_time is None or command_time > status_time:
            return True
    return False


def _parse_iso_datetime(raw: str) -> datetime | None:
    value = raw.strip()
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _request_markdown(
    message: str,
    session_key: str,
    chat_id: str,
    sender_id: str,
    conversation_context: list[dict[str, Any]] | None = None,
) -> str:
    context_markdown = _conversation_context_markdown(conversation_context or [])
    brief_note = _brief_note(conversation_context or [])
    return f"""# GolemBot Office Request

session_key: {session_key}
chat_id: {chat_id}
sender_id: {sender_id}

## User Message

{message}
{context_markdown}
{brief_note}

## Execution Boundary

GolemBot owns IM channel and harness session management. IM-Collab owns only the durable office task protocol.
Use Codex + superpowers as the only orchestration layer. Prefer existing Feishu and office wheels over handwritten office logic.

## Acceptance Criteria

- Create or update local office artifacts.
- Publish to Feishu when requested by the caller.
- Write final delivery metadata to artifacts.json.
- Return Markdown that GolemBot can send to the source conversation.
"""


def _write_group_brief(
    task_dir: Path,
    chat_id: str,
    conversation_context: list[dict[str, Any]],
    brief_extractor: str = "rules",
    brief_api_key: str | None = None,
    evidence_extractor: Any | None = None,
) -> dict[str, Any] | None:
    if not conversation_context:
        return None
    if brief_extractor == "rules":
        brief = build_group_brief(chat_id=chat_id, messages=conversation_context)
    elif brief_extractor == "langextract-deepseek":
        selected_context = select_briefing_context(conversation_context, max_messages=60, recent_tail=16)
        extractor = evidence_extractor or extract_evidence
        evidence = extractor(
            selected_context,
            api_key=brief_api_key or os.environ.get("DEEPSEEK_API_KEY"),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
            model_id=os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL_ID),
        )
        (task_dir / "evidence.json").write_text(
            _json_dumps(
                {
                    "extractor": brief_extractor,
                    "source_message_count": len(selected_context),
                    "original_source_message_count": len(conversation_context),
                    "context_selected": True,
                    "evidence": evidence,
                }
            ),
            encoding="utf-8",
        )
        brief = build_group_brief_from_evidence(chat_id=chat_id, messages=selected_context, evidence_items=evidence)
    else:
        raise ValueError(f"unsupported brief_extractor: {brief_extractor}")
    (task_dir / "brief.json").write_text(_json_dumps(brief), encoding="utf-8")
    (task_dir / "brief.md").write_text(render_group_brief_markdown(brief), encoding="utf-8")
    return brief


def _append_confirmation_controls_to_request(task_dir: Path) -> None:
    confirmation_commands = [
        command
        for command in read_control_commands(task_dir)
        if command.get("type") in {"append_instruction", "confirm_instruction", "card_action"}
    ]
    if not confirmation_commands:
        return
    request_path = task_dir / "request.md"
    current = request_path.read_text(encoding="utf-8")
    if "## Confirmation Controls" in current:
        return
    lines = ["", "## Confirmation Controls"]
    for command in confirmation_commands:
        payload = json.dumps(command.get("payload", {}), ensure_ascii=False)
        lines.append(f"- {command.get('type')}: {payload}")
    request_path.write_text(current.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def _conversation_context_markdown(messages: list[dict[str, Any]]) -> str:
    if not messages:
        return ""
    lines = ["", "## Conversation Context", ""]
    for message in messages:
        sender = message.get("sender_id") or message.get("sender", {}).get("id") or "unknown"
        message_id = message.get("message_id") or message.get("id") or "unknown"
        content = str(message.get("content", "")).strip()
        if content:
            lines.append(f"- {sender} ({message_id}): {content}")
    return "\n".join(lines) + "\n"


def _brief_note(messages: list[dict[str, Any]]) -> str:
    if not messages:
        return ""
    return """
## Source-Grounded Group Brief

This task includes `brief.json` and `brief.md`. Treat them as the evidence layer for group-chat facts. Preserve message references when using requirements from the brief.
"""


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _task_id_from_session(session_key: str) -> str:
    return "gb-" + re.sub(r"[^A-Za-z0-9_.-]+", "-", session_key).strip("-")
