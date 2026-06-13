from __future__ import annotations

from dataclasses import replace
from getpass import getpass
from pathlib import Path

from .config import Settings, settings_to_env
from .storage import ensure_private_directory, ensure_private_file


def setup_missing_items(settings: Settings) -> list[str]:
    missing: list[str] = []
    if not settings.credentials_file.exists():
        missing.append(f"Google OAuth client file not found: {settings.credentials_file}")
    if not settings.sheet_id.strip():
        missing.append("Google Sheet ID is not configured.")
    if not settings.sheet_tab.strip():
        missing.append("Google Sheet tab is not configured.")
    if settings.enable_remote_ai and not settings.groq_api_key.strip():
        missing.append("Groq API key is required when remote AI is enabled.")
    return missing


def setup_complete(settings: Settings) -> bool:
    return not setup_missing_items(settings)


def run_setup_wizard(settings: Settings) -> Settings:
    ensure_private_directory(settings.sentinel_home)
    ensure_private_file(settings.env_file)

    print("Initial setup")
    print("Sentinel will store your token, state, and private config under your user directory.")
    print(f"Private config file: {settings.env_file}")
    print()

    profile_name = _prompt_text(
        "Optional profile name for this machine or user",
        default=settings.profile_name,
        required=False,
    )
    credentials_file = _prompt_path(
        "Path to your Google OAuth client JSON",
        default=settings.credentials_file,
        must_exist=True,
    )
    sheet_id = _prompt_text("Google Sheet ID", default=settings.sheet_id, required=True)
    sheet_tab = _prompt_text("Google Sheet tab", default=settings.sheet_tab or "Placements", required=True)
    enable_remote_ai = _prompt_yes_no("Enable remote AI with Groq?", default=settings.enable_remote_ai)
    groq_api_key = ""
    groq_model = settings.groq_model
    if enable_remote_ai:
        groq_api_key = _prompt_text("Groq API key", default=settings.groq_api_key, required=True, secret=True)
        groq_model = _prompt_text("Groq model", default=settings.groq_model, required=True)

    mail_max_results = _prompt_int("How many recent emails should Sentinel inspect", default=settings.mail_max_results)
    web_research_results = _prompt_int("How many web research results should Sentinel use", default=settings.web_research_results)

    updated = replace(
        settings,
        credentials_file=credentials_file,
        sheet_id=sheet_id,
        sheet_tab=sheet_tab,
        profile_name=profile_name,
        enable_remote_ai=enable_remote_ai,
        groq_api_key=groq_api_key,
        groq_model=groq_model,
        mail_max_results=mail_max_results,
        web_research_results=web_research_results,
        token_file=settings.token_file,
        state_file=settings.state_file,
    )
    _write_env_file(updated)
    print()
    print("Setup saved.")
    print("Next run will complete Gmail authorization and create your private token file.")
    return updated


def _write_env_file(settings: Settings) -> None:
    env_file = settings.env_file
    env_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={value}" for key, value in settings_to_env(settings).items()]
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ensure_private_file(env_file)


def _prompt_text(prompt: str, *, default: str = "", required: bool = False, secret: bool = False) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        if secret:
            raw = getpass(f"{prompt}{suffix}: ")
            value = raw.strip()
            if not value and default:
                value = default
        else:
            value = input(f"{prompt}{suffix}: ").strip()
            if not value and default:
                value = default
        if not value:
            if not required:
                return value
            print("This value is required.")
            continue
        return value


def _prompt_path(prompt: str, *, default: Path, must_exist: bool = False) -> Path:
    while True:
        raw = _prompt_text(prompt, default=str(default), required=True)
        path = Path(raw).expanduser()
        if not must_exist or path.exists():
            return path
        print(f"File not found: {path}")


def _prompt_int(prompt: str, *, default: int) -> int:
    while True:
        raw = _prompt_text(prompt, default=str(default), required=True)
        try:
            return int(raw)
        except ValueError:
            print("Please enter a whole number.")


def _prompt_yes_no(prompt: str, *, default: bool) -> bool:
    default_hint = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{prompt} [{default_hint}]: ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Please answer yes or no.")
