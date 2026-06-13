from __future__ import annotations

from pathlib import Path
import os


class _NoOpTaskOutputStorageHandler:
    def __init__(self) -> None:
        self._rows: list[dict] = []

    def update(self, task_index: int, log: dict) -> None:
        if len(self._rows) <= task_index:
            self._rows.extend({} for _ in range(task_index - len(self._rows) + 1))
        self._rows[task_index] = log

    def add(
        self,
        task,
        output: dict,
        task_index: int,
        inputs: dict | None = None,
        was_replayed: bool = False,
    ) -> None:
        if len(self._rows) <= task_index:
            self._rows.extend({} for _ in range(task_index - len(self._rows) + 1))
        self._rows[task_index] = {
            "task": task,
            "output": output,
            "task_index": task_index,
            "inputs": inputs or {},
            "was_replayed": was_replayed,
        }

    def reset(self) -> None:
        self._rows.clear()

    def load(self) -> list[dict]:
        return list(self._rows)


def configure_crewai_storage() -> Path:
    """Redirect CrewAI's default app-data storage into the project workspace."""
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

    storage_root = Path.cwd() / ".state" / "crewai"
    storage_root.mkdir(parents=True, exist_ok=True)

    try:
        import appdirs

        def _local_user_data_dir(appname: str, appauthor: str) -> str:
            path = storage_root / appauthor / appname
            path.mkdir(parents=True, exist_ok=True)
            return str(path)

        appdirs.user_data_dir = _local_user_data_dir  # type: ignore[assignment]
    except Exception:
        pass

    try:
        import crewai.memory.storage.kickoff_task_outputs_storage as kickoff_storage
        import crewai.utilities.task_output_storage_handler as task_output_handler

        kickoff_storage.KickoffTaskOutputsSQLiteStorage = _NoOpTaskOutputStorageHandler  # type: ignore[assignment]
        task_output_handler.TaskOutputStorageHandler = _NoOpTaskOutputStorageHandler  # type: ignore[assignment]
    except Exception:
        pass

    return storage_root
