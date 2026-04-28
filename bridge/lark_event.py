from __future__ import annotations

from pathlib import Path


def build_subscribe_args(
    output_dir: Path,
    event_types: str = "im.message.receive_v1",
    dry_run: bool = False,
) -> list[str]:
    args = [
        "lark-cli",
        "event",
        "+subscribe",
        "--as",
        "bot",
        "--event-types",
        event_types,
        "--compact",
        "--quiet",
        "--output-dir",
        output_dir.as_posix(),
    ]
    if dry_run:
        args.append("--dry-run")
    return args
