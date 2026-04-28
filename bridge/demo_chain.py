from __future__ import annotations

from pathlib import Path


def build_demo_chain_commands(
    assistant_dir: Path = Path(".experiments") / "golembot-codex",
    gateway_token: str = "local-golembot-spike",
    gateway_url: str = "http://127.0.0.1:3199",
    publish: bool = True,
    execute: bool = True,
    generator: str = "codex",
) -> dict[str, list[str]]:
    consumer = [
        ".venv/bin/python",
        "scripts/run_event_consumer.py",
        "--dispatch",
        "golembot",
        "--golembot-url",
        gateway_url,
        "--golembot-token",
        gateway_token,
        "--generator",
        generator,
    ]
    if publish:
        consumer.append("--publish")
    if execute:
        consumer.append("--execute")

    return {
        "golembot_gateway": [
            "npm",
            "exec",
            "--yes",
            "--package",
            "golembot@0.46.0",
            "--",
            "golembot",
            "gateway",
            "-d",
            assistant_dir.as_posix(),
            "--verbose",
        ],
        "feishu_listener": [
            ".venv/bin/python",
            "scripts/subscribe_feishu_events.py",
        ],
        "consumer": consumer,
    }
