"""warnBot: post new California WARN Act notices to Mastodon.

Each run:
  1. finds and downloads the current WARN report from the EDD site,
  2. parses the detailed report into rows,
  3. records rows not seen before in SQLite (the very first run only seeds:
     everything already in the report is marked as seen, nothing is posted),
  4. posts up to --max-posts pending notices, one post per notice, oldest first.

Run with `python -m warnbot.app`. Mastodon settings come from the environment
(MASTODON_HOST, MASTODON_TOKEN); see .env.example.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Callable

from warnbot import fetch
from warnbot.format import format_notice
from warnbot.parse import parse_report
from warnbot.store import Store

log = logging.getLogger("warnbot")

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "warnbot.db"

Poster = Callable[[str, str], dict]


def _default_poster(text: str, key: str) -> dict:
    from warnbot.create_msg import post_status  # needs Mastodon settings only when posting

    return post_status(text, idempotency_key=key)


def run(
    *,
    db: str | Path = DEFAULT_DB,
    max_posts: int = 20,
    dry_run: bool = False,
    report_url: str | None = None,
    report_file: str | Path | None = None,
    poster: Poster = _default_poster,
) -> dict:
    """One run of the pipeline. Returns counts for logging and tests."""
    if report_file:
        data = Path(report_file).read_bytes()
        source = str(report_file)
    else:
        source = report_url or fetch.find_report_url()
        data = fetch.download(source)
    rows = parse_report(data)
    log.info("Parsed %d rows from %s", len(rows), source)

    if dry_run:
        # Work on an in-memory copy so a dry run changes nothing on disk.
        store = Store(":memory:")
        if Path(db).exists():
            disk = Store(db)
            disk.db.backup(store.db)
            disk.close()
    else:
        store = Store(db)
    try:
        seed = store.is_empty()
        new = store.record(rows, seed=seed)
        if seed:
            log.info("First run: seeded %d existing notices without posting", len(new))
        else:
            log.info("%d new notices", len(new))

        posted = failed = 0
        for notice in store.pending(max_posts):
            text = format_notice(notice)
            if dry_run:
                print(f"--- would post ({notice['rows']} row(s)) ---\n{text}\n")
                continue
            try:
                result = poster(text, notice["notice_key"])
                store.mark_posted(notice["notice_key"], str(result.get("id")) if result else None)
                posted += 1
            except Exception as exc:  # keep going; the notice is retried next run
                log.warning("Posting %s failed: %s", notice["company"], exc)
                store.mark_failed(notice["notice_key"], str(exc))
                failed += 1
        counts = store.counts()
        log.info("Posted %d, failed %d; notices by status: %s", posted, failed, counts)
        return {"rows": len(rows), "new": len(new), "seeded": seed, "posted": posted, "failed": failed, "status": counts}
    finally:
        store.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="warnbot", description=__doc__.split("\n\n")[0])
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite file (default: data/warnbot.db)")
    parser.add_argument("--max-posts", type=int, default=20, help="most posts per run (default: 20)")
    parser.add_argument("--dry-run", action="store_true", help="print the posts; change nothing")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--report-url", help="report URL instead of discovering it")
    source.add_argument("--file", help="local .xlsx report instead of downloading")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        run(db=args.db, max_posts=args.max_posts, dry_run=args.dry_run, report_url=args.report_url, report_file=args.file)
    except Exception as exc:
        log.error("Run failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
