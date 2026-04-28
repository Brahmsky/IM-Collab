from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def check_tools(
    binaries: tuple[str, ...] = ("codex", "lark-cli", "skills", "node", "npm"),
    skill_names: tuple[str, ...] = ("lark-im", "lark-doc", "lark-slides", "lark-whiteboard"),
) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        "binaries": {name: _binary_status(name) for name in binaries},
        "skills": {name: _skill_status(name) for name in skill_names},
    }


def _binary_status(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {"available": path is not None, "path": path}


def _skill_status(name: str) -> dict[str, Any]:
    path = Path.home() / ".agents" / "skills" / name
    return {"available": path.is_dir(), "path": path.as_posix()}
