from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.config import Settings
from sentinel.pipeline import PlacementPipeline
from sentinel.state_store import StateStore


class StateStoreTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_state.json"
            store = StateStore(path)
            store.save_seen_message_ids({"a", "b"})
            self.assertEqual(store.load_seen_message_ids(), {"a", "b"})

    def test_dry_run_allows_missing_sheet_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            settings = Settings(
                sheet_id="",
                state_file=state_path,
            )
            pipeline = PlacementPipeline(settings)
            with patch("sentinel.gmail_service.GmailService.fetch_recent_messages", return_value=[]):
                self.assertEqual(pipeline.run(dry_run=True), [])


if __name__ == "__main__":
    unittest.main()

