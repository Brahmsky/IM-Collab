from __future__ import annotations

import json
import re
import subprocess
from html import escape
from pathlib import Path
from typing import Any, Callable

from bridge.lark_docs import _extract_json

Runner = Callable[[list[str]], str]


def markdown_to_slide_xml(markdown_path: Path, limit: int = 10) -> list[str]:
    text = markdown_path.read_text(encoding="utf-8")
    parts = re.split(r"(?m)^##\s+", text)
    slides: list[str] = []
    for part in parts[1:]:
        if len(slides) >= limit:
            break
        lines = [line.strip() for line in part.strip().splitlines() if line.strip()]
        if not lines:
            continue
        title = lines[0]
        body_lines = [line.lstrip("- ").strip() for line in lines[1:] if line.strip()]
        slides.append(_slide_xml(title, body_lines))
    return slides


def build_create_slides_args(slides: list[str], title: str, dry_run: bool = False) -> list[str]:
    args = [
        "lark-cli",
        "slides",
        "+create",
        "--as",
        "user",
        "--title",
        title,
        "--slides",
        json.dumps(slides, ensure_ascii=False),
    ]
    if dry_run:
        args.append("--dry-run")
    return args


def create_slides_from_markdown(
    markdown_path: Path,
    title: str,
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    slides = markdown_to_slide_xml(markdown_path)
    args = build_create_slides_args(slides, title=title, dry_run=dry_run)
    output = runner(args) if runner else _subprocess_runner(args)
    return {"ok": True, "dry_run": dry_run, "response": _extract_json(output), "raw": output}


def _slide_xml(title: str, body_lines: list[str]) -> str:
    body = "".join(f"<li><p>{escape(line)}</p></li>" for line in body_lines[:5])
    if not body:
        body = "<li><p>Generated from IM-Collab task context.</p></li>"
    return (
        '<slide xmlns="http://www.larkoffice.com/sml/2.0">'
        '<style><fill><fillColor color="rgb(248,250,252)"/></fill></style>'
        "<data>"
        '<shape type="text" topLeftX="80" topLeftY="80" width="800" height="100">'
        f'<content textType="title"><p>{escape(title)}</p></content>'
        "</shape>"
        '<shape type="text" topLeftX="90" topLeftY="210" width="820" height="320">'
        f'<content textType="body"><ul>{body}</ul></content>'
        "</shape>"
        "</data>"
        "</slide>"
    )


def _subprocess_runner(args: list[str]) -> str:
    completed = subprocess.run(args, check=True, text=True, capture_output=True)
    return completed.stdout
