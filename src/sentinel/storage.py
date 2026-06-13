from __future__ import annotations

import os
from pathlib import Path


def ensure_private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _apply_private_permissions(path, is_directory=True)


def ensure_private_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    _apply_private_permissions(path, is_directory=False)


def _apply_private_permissions(path: Path, *, is_directory: bool) -> None:
    try:
        if os.name != "nt":
            path.chmod(0o700 if is_directory else 0o600)
    except OSError:
        # Best effort only; on some filesystems or platforms permissions may be ignored.
        pass

