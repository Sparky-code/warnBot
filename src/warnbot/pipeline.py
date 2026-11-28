"""One run of the pipeline: post new California WARN Act notices to Mastodon.

Each run:
  1. finds and downloads the current WARN report from the EDD site,
  2. parses the detailed report into rows,
  3. records rows not seen before in SQLite (the very first run only seeds:
     everything already in the report is marked as seen, nothing is posted),
  4. posts up to `max_posts` pending notices, one post per notice, oldest first.

The CLI (`warnbot run`) wraps this in the job runner, which holds the run
lock, records the run and alerts on failure.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

from warnbot import fetch
from warnbot.format import format_notice
from warnbot.parse import parse_report
from warnbot.store import Store

Poster = Callable[[str, str], dict[str, Any]]


def _default_poster(text: str, key: str) -> dict[str, Any]:
    from warnbot.mastodon import post_status

    return post_status(text, idempotency_key=key)


class PostsFailedError(RuntimeError):
    """Some posts failed. They are retried on later runs; raised so the run alerts."""


def run(
    conn: sqlite3.Connection,
    *,
    max_posts: int = 20,
    dry_run: bool = False,
    report_url: str | None = None,
    report_file: str | Path | None = None,
    poster: Poster = _default_poster,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Run the pipeline against `conn`. Returns counts for logging and tests.

    A dry run works on an in-memory copy of the database, so it changes no
    notice state. Raises PostsFailedError after the run if any post failed.
    """
    if report_file:
        data = Path(report_file).read_bytes()
        source = str(report_file)
    else:
        source = report_url or fetch.find_report_url()
        data = fetch.download(source)
    rows = parse_report(data)
    log(f"Parsed {len(rows)} rows from {source}")

    if dry_run:
        copy = sqlite3.connect(":memory:", autocommit=False)
        conn.backup(copy)
        store = Store(copy)
    else:
        store = Store(conn)
    try:
        seed = store.is_empty()
        new = store.record(rows, seed=seed)
        if seed:
            log(f"First run: seeded {len(new)} existing notices without posting")
        else:
            log(f"{len(new)} new notices")

        posted = 0
        errors: list[str] = []
        for notice in store.pending(max_posts):
            text = format_notice(notice)
            if dry_run:
                log(f"--- would post ({notice['rows']} row(s)) ---\n{text}\n")
                continue
            try:
                result = poster(text, notice["notice_key"])
                status_id = str(result.get("id")) if result else None
                store.mark_posted(notice["notice_key"], status_id)
                posted += 1
            except Exception as exc:  # keep going; the notice is retried next run
                log(f"Posting {notice['company']} failed: {exc}")
                store.mark_failed(notice["notice_key"], str(exc))
                errors.append(str(exc))
        counts = store.counts()
    finally:
        if dry_run:
            store.db.close()

    summary = {
        "rows": len(rows),
        "new": len(new),
        "seeded": seed,
        "posted": posted,
        "failed": len(errors),
        "status": counts,
    }
    log(f"Posted {posted}, failed {len(errors)}; notices by status: {counts}")
    if errors:
        raise PostsFailedError(f"{len(errors)} post(s) failed, last: {errors[-1]}")
    return summary


def describe(summary: dict[str, Any]) -> str:
    """One line for the run record."""
    if summary["seeded"]:
        return f"seeded {summary['new']} notices from {summary['rows']} rows"
    return f"{summary['rows']} rows, {summary['new']} new notices, {summary['posted']} posted"
