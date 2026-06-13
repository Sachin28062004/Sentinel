from __future__ import annotations

from .config import Settings
from .crew_pipeline import analyze_email_with_crew
from .gmail_service import GmailService
from .models import EmailRecord, PlacementExtraction, PlacementRow
from .sheets_service import SheetsService
from .state_store import StateStore


class PlacementPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.gmail = GmailService(settings.credentials_file, settings.token_file, settings.scopes)
        self.sheets = SheetsService(
            settings.credentials_file,
            settings.token_file,
            settings.scopes,
            settings.sheet_id,
            settings.sheet_tab,
        )
        self.state = StateStore(settings.state_file)

    def run(self, days_back: int = 7, dry_run: bool = False) -> list[PlacementRow]:
        if not dry_run and not self.settings.sheet_id:
            raise ValueError("GOOGLE_SHEET_ID is required.")

        if not dry_run:
            self.sheets.ensure_header_row()
        seen = self.state.load_seen_message_ids()
        processed: set[str] = set(seen)
        appended_rows: list[PlacementRow] = []
        query = f"newer_than:{days_back}d"

        for email in self.gmail.fetch_recent_messages(self.settings.mail_max_results, query=query):
            if email.message_id in seen:
                continue

            extraction = analyze_email_with_crew(self.settings, email)
            if not extraction.is_placement_related:
                processed.add(email.message_id)
                continue

            row = self._build_row(email, extraction)
            if not dry_run:
                self.sheets.append_row(row)
            processed.add(email.message_id)
            appended_rows.append(row)

        if not dry_run:
            self.state.save_seen_message_ids(processed)
        return appended_rows

    def _build_row(self, email: EmailRecord, extraction: PlacementExtraction) -> PlacementRow:
        date_applied = extraction.date_applied or email.internal_date.strftime("%d-%m-%Y")
        return PlacementRow(
            company_name=extraction.company_name,
            date_applied=date_applied,
            role=extraction.role,
            application_link=extraction.application_link,
            status=extraction.status,
            job_type=extraction.job_type,
        )
