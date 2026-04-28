from __future__ import annotations

from bridge.demo_chain import build_demo_chain_commands


def test_build_demo_chain_commands_defaults_to_golembot_publish_execute() -> None:
    commands = build_demo_chain_commands()

    assert commands["golembot_gateway"][0:3] == ["npm", "exec", "--yes"]
    assert "golembot@0.46.0" in commands["golembot_gateway"]
    assert commands["feishu_listener"][0:2] == [".venv/bin/python", "scripts/subscribe_feishu_events.py"]
    assert commands["consumer"][0:2] == [".venv/bin/python", "scripts/run_event_consumer.py"]
    assert "--dispatch" in commands["consumer"]
    assert "golembot" in commands["consumer"]
    assert "--publish" in commands["consumer"]
    assert "--execute" in commands["consumer"]
    assert "--generator" in commands["consumer"]
    assert "codex" in commands["consumer"]


def test_build_demo_chain_commands_can_disable_real_reply() -> None:
    commands = build_demo_chain_commands(publish=False, execute=False)

    assert "--publish" not in commands["consumer"]
    assert "--execute" not in commands["consumer"]
