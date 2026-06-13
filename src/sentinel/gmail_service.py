from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from typing import Any

try:
    from bs4 import BeautifulSoup
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ModuleNotFoundError:
    BeautifulSoup = None
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None

from .models import EmailRecord


class GmailService:
    def __init__(self, credentials_file: Path, token_file: Path, scopes: list[str]) -> None:
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = scopes
        self._service = None
        self._available = all(
            dependency is not None
            for dependency in (BeautifulSoup, Request, Credentials, InstalledAppFlow, build)
        )

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
            raise RuntimeError("Google API client libraries are not installed; Gmail access is unavailable.")
        if self._service is None:
            self._service = build("gmail", "v1", credentials=self._get_credentials())
        return self._service

    def fetch_recent_messages(self, max_results: int = 25, query: str | None = None) -> list[EmailRecord]:
        if not self._available:
            return []
        response = (
            self.service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=max_results, q=query)
            .execute()
        )
        message_refs = response.get("messages", [])
        messages: list[EmailRecord] = []
        for ref in message_refs:
            payload = (
                self.service.users()
                .messages()
                .get(userId="me", id=ref["id"], format="full")
                .execute()
            )
            messages.append(self._to_email_record(payload))
        messages.sort(key=lambda record: record.internal_date, reverse=True)
        return messages

    def _to_email_record(self, payload: dict[str, Any]) -> EmailRecord:
        headers = {header["name"].lower(): header["value"] for header in payload.get("payload", {}).get("headers", [])}
        body_text = self._extract_body_text(payload.get("payload", {}))
        internal_ms = int(payload.get("internalDate", "0"))
        return EmailRecord(
            message_id=payload["id"],
            thread_id=payload.get("threadId", ""),
            internal_date=datetime.fromtimestamp(internal_ms / 1000, tz=timezone.utc),
            from_email=headers.get("from", ""),
            subject=headers.get("subject", ""),
            snippet=payload.get("snippet", ""),
            body_text=body_text,
            raw_payload=payload,
        )

    def _extract_body_text(self, payload: dict[str, Any]) -> str:
        parts = payload.get("parts", [])
        mime_type = payload.get("mimeType", "")
        body = payload.get("body", {})

        if mime_type == "text/plain" and body.get("data"):
            return self._decode_body(body["data"])

        if mime_type == "text/html" and body.get("data"):
            html = self._decode_body(body["data"])
            return self._html_to_text(html)

        if body.get("data") and not parts:
            decoded = self._decode_body(body["data"])
            return self._html_to_text(decoded) if "<html" in decoded.lower() or "<body" in decoded.lower() else decoded

        texts: list[str] = []
        for part in parts:
            part_text = self._extract_body_text(part)
            if part_text:
                texts.append(part_text)
        return "\n".join(texts).strip()

    @staticmethod
    def _decode_body(data: str) -> str:
        padding = "=" * (-len(data) % 4)
        decoded = base64.urlsafe_b64decode(data + padding)
        return decoded.decode("utf-8", errors="replace")

    @staticmethod
    def _html_to_text(html: str) -> str:
        if BeautifulSoup is None:
            return html
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return " ".join(soup.get_text(" ", strip=True).split())
