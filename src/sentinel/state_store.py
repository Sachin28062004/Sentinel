from __future__ import annotations

import json
from pathlib import Path


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load_seen_message_ids(self) -> set[str]:
        if not self.path.exists():
            return set()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return set()
        return set(data.get("seen_message_ids", []))

    def save_seen_message_ids(self, message_ids: set[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"seen_message_ids": sorted(message_ids)}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

