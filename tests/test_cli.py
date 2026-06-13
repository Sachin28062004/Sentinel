from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.models import PlacementRow
from sentinel import cli


class CliTests(unittest.TestCase):
    def test_default_run_command_uses_common_flags(self) -> None:
        fake_settings = SimpleNamespace(
            profile_name="default",
            sentinel_home=Path.home() / ".sentinel",
            env_file=Path.home() / ".sentinel" / ".env",
        )
        fake_pipeline = SimpleNamespace(
            run=lambda **kwargs: [
                PlacementRow(
                    company_name="Acme",
                    date_applied="01-01-2026",
                    role="Software Engineer",
                    application_link="https://example.com/apply",
                    status="Pending",
                    job_type="Full Time",
                )
            ]
        )

        with (
            patch.object(cli, "get_settings", return_value=fake_settings),
            patch.object(cli, "setup_complete", return_value=True),
            patch.object(cli, "PlacementPipeline", return_value=fake_pipeline),
        ):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = cli.main(["--dry-run", "--json"])

        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        self.assertIn("""
------------------------------------------------------------------------------

███████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗              
██╔════╝██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║              
███████╗█████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║              
╚════██║██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║              
███████║███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗██╗██╗██╗
╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝╚═╝╚═╝
-------------------------------------------------------------------------------

Placement email triage and Google Sheets sync agent

Searching for Latest placement mails...  
                                                                      
Result: """, output)
        self.assertIn('"company_name": "Acme"', output)
        self.assertIn("Processed 1 placement email(s).", output)

    def test_doctor_command_reports_environment(self) -> None:
        fake_settings = SimpleNamespace(
            credentials_file=Path("credentials.json"),
            token_file=Path("token.json"),
            state_file=Path(".state/processed_messages.json"),
            profile_name="default",
            sentinel_home=Path.home() / ".sentinel",
            env_file=Path.home() / ".sentinel" / ".env",
            enable_remote_ai=False,
            sheet_id="",
            sheet_tab="Placements",
            mail_max_results=25,
            web_research_results=5,
        )

        with patch.object(cli, "get_settings", return_value=fake_settings):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = cli.main(["doctor"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Sentinel environment", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
