from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Sequence

from . import __version__
from .config import get_settings
from .pipeline import PlacementPipeline
from .setup import run_setup_wizard, setup_complete, setup_missing_items


BANNER = "Sentinel - Placement email triage and Google Sheets sync agent"


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    _add_common_run_arguments(common)

    parser = argparse.ArgumentParser(
        prog="sentinel",
        description="Run the Sentinel placement email workflow from the command line.",
        parents=[common],
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser(
        "run",
        help="Process recent emails once and append matching rows to Google Sheets.",
        parents=[common],
    )
    run_parser.set_defaults(func=_run_once)

    daemon_parser = subparsers.add_parser(
        "daemon",
        help="Keep running and execute the workflow on a fixed interval.",
        parents=[common],
    )
    daemon_parser.add_argument(
        "--interval-hours",
        type=int,
        default=3,
        help="Hours between automatic runs.",
    )
    daemon_parser.set_defaults(func=_run_forever)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Check local configuration and report what is ready or missing.",
    )
    doctor_parser.set_defaults(func=_doctor)

    setup_parser = subparsers.add_parser(
        "setup",
        help="Walk through first-time setup and save private config under your user directory.",
    )
    setup_parser.set_defaults(func=_setup)

    parser.set_defaults(func=_default_dispatch)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


def _add_common_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--days-back", type=int, default=7, help="Only inspect messages newer than this many days.")
    parser.add_argument("--dry-run", action="store_true", help="Run the workflow without writing to Google Sheets.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the result rows as JSON instead of human-readable text.",
    )


def _default_dispatch(args: argparse.Namespace) -> int:
    settings = get_settings()
    _print_banner()
    if not setup_complete(settings):
        _print_missing_setup(settings)
        if _prompt_yes_no("Run initial setup now?", default=True):
            run_setup_wizard(settings)
        return 0
    return _run_once(args, settings=settings, show_banner=False)


def _setup(args: argparse.Namespace) -> int:
    _print_banner()
    run_setup_wizard(get_settings())
    return 0


def _run_once(args: argparse.Namespace, settings=None, *, show_banner: bool = True) -> int:
    settings = settings or get_settings()
    if show_banner:
        _print_banner()
    _ensure_setup_or_exit(settings)
    pipeline = PlacementPipeline(settings)
    rows = pipeline.run(days_back=args.days_back, dry_run=args.dry_run)
    _print_rows(rows, json_output=args.json)
    print(f"Processed {len(rows)} placement email(s).")
    return 0


def _run_forever(args: argparse.Namespace) -> int:
    settings = get_settings()
    _print_banner()
    _ensure_setup_or_exit(settings)
    pipeline = PlacementPipeline(settings)
    interval_seconds = max(1, args.interval_hours) * 60 * 60
    print(f"Running every {args.interval_hours} hour(s). Press Ctrl+C to stop.")
    while True:
        started_at = datetime.now(timezone.utc)
        try:
            rows = pipeline.run(days_back=args.days_back, dry_run=args.dry_run)
            _print_rows(rows, json_output=args.json)
            print(f"[{started_at.astimezone().isoformat(timespec='seconds')}] Processed {len(rows)} placement email(s).")
        except Exception as exc:
            print(f"[{started_at.astimezone().isoformat(timespec='seconds')}] Run failed: {type(exc).__name__}: {exc}")

        next_run = datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)
        print(f"Next run at {next_run.astimezone().isoformat(timespec='seconds')}")
        try:
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("Stopped.")
            return 0


def _doctor(args: argparse.Namespace) -> int:
    settings = get_settings()
    _print_banner()
    print("Sentinel environment")
    print(f"Version: {__version__}")
    print(f"Groq enabled: {'yes' if settings.enable_remote_ai else 'no'}")
    print(f"Profile: {settings.profile_name or 'default'}")
    print(f"Private home: {settings.sentinel_home}")
    print(f"Google sheet id: {'set' if settings.sheet_id else 'missing'}")
    print(f"Google sheet tab: {settings.sheet_tab}")
    print(f"Mail max results: {settings.mail_max_results}")
    print(f"Web research results: {settings.web_research_results}")
    print(f"Private config file: {settings.env_file}")
    for label, path in [
        ("Google credentials file", settings.credentials_file),
        ("Google token file", settings.token_file),
        ("State file", settings.state_file),
    ]:
        exists = path.exists()
        print(f"{label}: {path} ({'found' if exists else 'missing'})")
    missing = setup_missing_items(settings)
    if missing:
        print("Setup status: incomplete")
        for item in missing:
            print(f"- {item}")
    else:
        print("Setup status: complete")
    return 0


def _ensure_setup_or_exit(settings) -> None:
    if setup_complete(settings):
        return
    _print_missing_setup(settings)
    if not _prompt_yes_no("Run initial setup now?", default=True):
        raise SystemExit(0)
    run_setup_wizard(settings)
    raise SystemExit(0)


def _print_missing_setup(settings) -> None:
    print("Initial setup is not complete.")
    for item in setup_missing_items(settings):
        print(f"- {item}")


def _print_banner() -> None:
    print(BANNER)


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


def _print_rows(rows, *, json_output: bool) -> None:
    payload = [asdict(row) for row in rows]
    if json_output:
        print(json.dumps(payload, indent=2))
        return
    if not payload:
        print("No placement rows found.")
        return
    for row in payload:
        print(
            f"- {row['company_name']} | {row['role']} | {row['date_applied']} | "
            f"{row['status']} | {row['job_type']} | {row['application_link']}"
        )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
