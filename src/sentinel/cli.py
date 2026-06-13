from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone

from .config import get_settings
from .pipeline import PlacementPipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=7)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--daemon", action="store_true", help="Keep running and execute every interval.")
    parser.add_argument("--interval-hours", type=int, default=3, help="Hours between automatic runs.")
    args = parser.parse_args()

    settings = get_settings()
    pipeline = PlacementPipeline(settings)
    if args.daemon:
        _run_forever(pipeline, days_back=args.days_back, dry_run=args.dry_run, interval_hours=args.interval_hours)
        return

    rows = pipeline.run(days_back=args.days_back, dry_run=args.dry_run)
    print(json.dumps([row.__dict__ for row in rows], indent=2))
    print(f"Processed {len(rows)} placement email(s).")


def _run_forever(pipeline: PlacementPipeline, days_back: int, dry_run: bool, interval_hours: int) -> None:
    interval_seconds = max(1, interval_hours) * 60 * 60
    print(f"Running every {interval_hours} hour(s). Press Ctrl+C to stop.")
    while True:
        started_at = datetime.now(timezone.utc)
        try:
            rows = pipeline.run(days_back=days_back, dry_run=dry_run)
            print(json.dumps([row.__dict__ for row in rows], indent=2))
            print(f"[{started_at.astimezone().isoformat(timespec='seconds')}] Processed {len(rows)} placement email(s).")
        except Exception as exc:
            print(f"[{started_at.astimezone().isoformat(timespec='seconds')}] Run failed: {type(exc).__name__}: {exc}")

        next_run = datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)
        print(f"Next run at {next_run.astimezone().isoformat(timespec='seconds')}")
        try:
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("Stopped.")
            return


if __name__ == "__main__":
    main()
