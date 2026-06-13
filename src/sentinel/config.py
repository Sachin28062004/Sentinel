from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*args, **kwargs):  # type: ignore[unused-ignore]
        return False


def get_sentinel_home() -> Path:
    profile = os.getenv("SENTINEL_PROFILE", "").strip()
    if profile:
        return (Path.home() / ".sentinel" / profile).expanduser()
    return Path(os.getenv("SENTINEL_HOME", str(Path.home() / ".sentinel"))).expanduser()


def get_sentinel_env_file() -> Path:
    return Path(os.getenv("SENTINEL_ENV_FILE", str(Path.home() / ".sentinel" / ".env"))).expanduser()


def load_private_environment() -> None:
    env_file = get_sentinel_env_file()
    if env_file.exists():
        load_dotenv(env_file, override=False)


load_private_environment()


def _split_scopes(raw: str) -> list[str]:
    return [scope.strip() for scope in raw.split(",") if scope.strip()]


def _read_env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _read_path(name: str, default: Path) -> Path:
    return Path(os.getenv(name, str(default))).expanduser()


@dataclass(frozen=True)
class Settings:
    sentinel_home: Path = get_sentinel_home()
    env_file: Path = get_sentinel_env_file()
    profile_name: str = _read_env("SENTINEL_PROFILE", "")
    groq_api_key: str = _read_env("GROQ_API_KEY", "")
    groq_model: str = _read_env("GROQ_MODEL", "groq/llama-3.3-70b-versatile")
    credentials_file: Path = _read_path("GOOGLE_CREDENTIALS_FILE", get_sentinel_home() / "credentials.json")
    token_file: Path = _read_path("GOOGLE_TOKEN_FILE", get_sentinel_home() / "token.json")
    scopes: list[str] = field(
        default_factory=lambda: _split_scopes(
            _read_env(
                "GOOGLE_SCOPES",
                "https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/spreadsheets",
            )
        )
    )
    sheet_id: str = _read_env("GOOGLE_SHEET_ID", "")
    sheet_tab: str = _read_env("GOOGLE_SHEET_TAB", "Placements")
    mail_max_results: int = int(_read_env("MAIL_MAX_RESULTS", "25"))
    web_research_results: int = int(_read_env("WEB_RESEARCH_RESULTS", "5"))
    state_file: Path = _read_path("STATE_FILE", get_sentinel_home() / "state" / "processed_messages.json")
    enable_remote_ai: bool = _read_env("ENABLE_REMOTE_AI", "false").lower() == "true"


def get_settings() -> Settings:
    return Settings()


def settings_to_env(settings: Settings) -> dict[str, str]:
    payload: dict[str, str] = {
        "SENTINEL_HOME": str(settings.sentinel_home),
        "GOOGLE_CREDENTIALS_FILE": str(settings.credentials_file),
        "GOOGLE_TOKEN_FILE": str(settings.token_file),
        "GOOGLE_SCOPES": ",".join(settings.scopes),
        "GOOGLE_SHEET_ID": settings.sheet_id,
        "GOOGLE_SHEET_TAB": settings.sheet_tab,
        "MAIL_MAX_RESULTS": str(settings.mail_max_results),
        "WEB_RESEARCH_RESULTS": str(settings.web_research_results),
        "STATE_FILE": str(settings.state_file),
        "ENABLE_REMOTE_AI": "true" if settings.enable_remote_ai else "false",
    }
    if settings.groq_api_key:
        payload["GROQ_API_KEY"] = settings.groq_api_key
    if settings.groq_model:
        payload["GROQ_MODEL"] = settings.groq_model
    if settings.profile_name:
        payload["SENTINEL_PROFILE"] = settings.profile_name
    return payload


def load_settings_from_env_file(env_file: Path | None = None) -> Settings:
    if env_file is not None and env_file.exists():
        load_dotenv(env_file, override=True)
    elif get_sentinel_env_file().exists():
        load_dotenv(get_sentinel_env_file(), override=True)
    return Settings()
