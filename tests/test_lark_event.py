from __future__ import annotations

from pathlib import Path

from bridge.lark_event import build_subscribe_args


def test_build_subscribe_args_uses_existing_lark_cli_event_wheel() -> None:
    args = build_subscribe_args(output_dir=Path("events/im"))

    assert args == [
        "lark-cli",
        "event",
        "+subscribe",
        "--as",
        "bot",
        "--event-types",
        "im.message.receive_v1",
        "--compact",
        "--quiet",
        "--output-dir",
        "events/im",
    ]


def test_build_subscribe_args_supports_dry_run() -> None:
    args = build_subscribe_args(output_dir=Path("events/im"), dry_run=True)

    assert args[-1] == "--dry-run"
