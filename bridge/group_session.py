from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


NEW_PREFIX = "/new"
LOOKBACK_RE = re.compile(r"^(?:(?P<days>\d+)d)?(?:(?P<hours>\d+)h)?$")
NEW_COMMAND_RE = re.compile(r"(^|\s)(/new)(?=\s|$)")


@dataclass(frozen=True)
class NewSessionCommand:
    instruction: str
    lookback: timedelta | None = None


def parse_new_session_command(text: str) -> NewSessionCommand | None:
    value = text.strip()
    match = NEW_COMMAND_RE.search(value)
    if not match:
        return None
    rest = value[match.start(2) + len(NEW_PREFIX) :].strip()
    if not rest:
        return NewSessionCommand(instruction="")
    first, _, tail = rest.partition(" ")
    lookback = _parse_lookback(first)
    if lookback is None:
        return NewSessionCommand(instruction=rest)
    return NewSessionCommand(instruction=tail.strip(), lookback=lookback)


def collect_new_session_context(
    messages: list[dict[str, Any]],
    *,
    trigger_message_id: str,
    command: NewSessionCommand | None,
    now: datetime | None = None,
    max_messages: int = 80,
) -> list[dict[str, Any]]:
    if max_messages <= 0:
        return []
    if command is None:
        return _without_trigger(messages, trigger_message_id)[-max_messages:]
    trigger_time = _trigger_time(messages, trigger_message_id)
    cutoff_now = _now_utc(now) if now is not None else trigger_time or _now_utc(None)
    cutoff = cutoff_now - command.lookback if command.lookback is not None else None
    selected: list[dict[str, Any]] = []
    for message in _without_trigger(messages, trigger_message_id):
        if cutoff is not None:
            sent_at = _message_time(message)
            if sent_at is None or sent_at < cutoff:
                continue
        elif _is_new_command_message(message):
            selected = []
            continue
        selected.append(message)
    return selected[-max_messages:]


def collect_group_delta_context(
    messages: list[dict[str, Any]],
    *,
    last_absorbed_message_id: str,
    trigger_message_id: str,
    max_messages: int = 80,
) -> list[dict[str, Any]]:
    if max_messages <= 0:
        return []
    selected: list[dict[str, Any]] = []
    boundary_seen = False
    for message in messages:
        message_id = str(message.get("message_id") or message.get("id") or "")
        if not message_id or message_id == trigger_message_id:
            continue
        if boundary_seen:
            selected.append(message)
            continue
        if message_id == last_absorbed_message_id:
            boundary_seen = True
    if boundary_seen:
        return selected[-max_messages:]
    return _without_trigger(messages, trigger_message_id)[-max_messages:]


def _parse_lookback(value: str) -> timedelta | None:
    match = LOOKBACK_RE.match(value)
    if not match:
        return None
    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    if days == 0 and hours == 0:
        return None
    return timedelta(days=days, hours=hours)


def _without_trigger(messages: list[dict[str, Any]], trigger_message_id: str) -> list[dict[str, Any]]:
    return [message for message in messages if str(message.get("message_id") or message.get("id") or "") != trigger_message_id]


def _trigger_time(messages: list[dict[str, Any]], trigger_message_id: str) -> datetime | None:
    for message in messages:
        if str(message.get("message_id") or message.get("id") or "") == trigger_message_id:
            return _message_time(message)
    return None


def _is_new_command_message(message: dict[str, Any]) -> bool:
    return str(message.get("content") or message.get("text") or "").strip().startswith(f"{NEW_PREFIX} ")


def _message_time(message: dict[str, Any]) -> datetime | None:
    raw = str(message.get("sent_at") or message.get("create_time") or message.get("timestamp") or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        value = int(raw)
        if value > 10_000_000_000:
            value = value // 1000
        return datetime.fromtimestamp(value, tz=UTC)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _now_utc(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)
