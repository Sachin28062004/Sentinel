from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*args, **kwargs):  # type: ignore[unused-ignore]
        return False


load_dotenv()


def _split_scopes(raw: str) -> list[str]:
    return [scope.strip() for scope in raw.split(",") if scope.strip()]


@dataclass(frozen=True)
class Settings:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "groq/llama-3.3-70b-versatile")
    credentials_file: Path = Path(os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"))
    token_file: Path = Path(os.getenv("GOOGLE_TOKEN_FILE", "token.json"))
    scopes: list[str] = field(
        default_factory=lambda: _split_scopes(
            os.getenv(
                "GOOGLE_SCOPES",
                "https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/spreadsheets",
            )
        )
    )
    sheet_id: str = os.getenv("GOOGLE_SHEET_ID", "")
    sheet_tab: str = os.getenv("GOOGLE_SHEET_TAB", "Placements")
    mail_max_results: int = int(os.getenv("MAIL_MAX_RESULTS", "25"))
    web_research_results: int = int(os.getenv("WEB_RESEARCH_RESULTS", "5"))
    state_file: Path = Path(os.getenv("STATE_FILE", ".state/processed_messages.json"))
    enable_remote_ai: bool = os.getenv("ENABLE_REMOTE_AI", "false").lower() == "true"


def get_settings() -> Settings:
    return Settings()
