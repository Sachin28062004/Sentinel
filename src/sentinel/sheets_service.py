from __future__ import annotations

from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ModuleNotFoundError:
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None

from .models import PlacementRow

PLACEMENT_SHEET_HEADERS = [
    "Company Name",
    "Date Applied",
    "Role",
    "Application Link",
    "Status",
    "Job Type",
]


class SheetsService:
    def __init__(self, credentials_file: Path, token_file: Path, scopes: list[str], sheet_id: str, sheet_tab: str) -> None:
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = scopes
        self.sheet_id = sheet_id
        self.sheet_tab = sheet_tab
        self._service = None
        self._available = all(dependency is not None for dependency in (Request, Credentials, InstalledAppFlow, build))

    def _get_credentials(self) -> Credentials:
        if not self._available:
            return None  # type: ignore[return-value]
        creds = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), self.scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), self.scopes)
                creds = flow.run_local_server(port=0)
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
        return creds

    @property
    def service(self):
        if not self._available:
            raise RuntimeError("Google API client libraries are not installed; Sheets access is unavailable.")
        if self._service is None:
            self._service = build("sheets", "v4", credentials=self._get_credentials())
        return self._service

    def append_row(self, row: PlacementRow) -> dict:
        if not self._available:
            return {}
        values = [[
            row.company_name,
            row.date_applied,
            row.role,
            row.application_link,
            row.status,
            row.job_type,
        ]]
        return (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.sheet_id,
                range=self.sheet_tab,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": values},
            )
            .execute()
        )

    def ensure_header_row(self) -> None:
        if not self._available:
            return
        self.service.spreadsheets().values().update(
            spreadsheetId=self.sheet_id,
            range=f"{self.sheet_tab}!A1:F1",
            valueInputOption="USER_ENTERED",
            body={"values": [PLACEMENT_SHEET_HEADERS]},
        ).execute()
