from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import scripts.run_event_consumer as run_event_consumer
from scripts.run_event_consumer import build_config


def test_build_config_uses_relative_event_dir_and_state_file() -> None:
    config = build_config(bot_open_ids=("ou_bot",))

    assert config.event_dir.as_posix() == "events/im"
    assert config.tasks_root.as_posix() == "tasks"
    assert config.state_path.as_posix() == "events/im/.consumer-state.json"
    assert config.bot_open_ids == frozenset({"ou_bot"})


def test_golembot_handler_passes_tasks_root_to_dispatch(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_dispatch(event_path: Path, **kwargs) -> None:
        seen["event_path"] = event_path
        seen.update(kwargs)

    monkeypatch.setattr(run_event_consumer, "dispatch_event_via_golembot", fake_dispatch)
    args = SimpleNamespace(
        dispatch="golembot",
        golembot_url="http://127.0.0.1:3199",
        golembot_token="token",
        publish=True,
        generator="codex",
        execute=True,
    )
    config = build_config(tasks_root=Path("/tmp/tasks"))

    handler = run_event_consumer.build_handler(args, config)
    handler(Path("/tmp/event.json"))

    assert seen["event_path"] == Path("/tmp/event.json")
    assert seen["tasks_root"] == Path("/tmp/tasks")


def test_golembot_handler_passes_app_server_generator(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_dispatch(event_path: Path, **kwargs) -> None:
        seen.update(kwargs)

    monkeypatch.setattr(run_event_consumer, "dispatch_event_via_golembot", fake_dispatch)
    args = SimpleNamespace(
        dispatch="golembot",
        golembot_url="http://127.0.0.1:3199",
        golembot_token="token",
        publish=False,
        generator="app-server",
        execute=False,
    )

    run_event_consumer.build_handler(args, build_config())(Path("/tmp/event.json"))

    assert seen["generator"] == "app-server"
