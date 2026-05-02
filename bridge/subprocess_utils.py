from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any


def resolve_cmd(args: list[str]) -> list[str]:
    """Resolve the first element (command name) to its full path on Windows."""
    if os.name == "nt":
        resolved = shutil.which(args[0])
        if resolved:
            return [resolved, *args[1:]]
    return args


def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(resolve_cmd(args), **kwargs)


def Popen(args: list[str], **kwargs: Any) -> subprocess.Popen[str]:
    return subprocess.Popen(resolve_cmd(args), **kwargs)
