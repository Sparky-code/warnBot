from __future__ import annotations

from typing import Any

from tests.conftest import make_report, row
from warnbot import db
from warnbot.parse import parse_report
from warnbot.store import MAX_ATTEMPTS, Store


def parsed(rows: list[list[Any]]) -> list[dict[str, Any]]:
    return parse_report(make_report(rows))


def test_first_run_seeds_and_posts_nothing(report_rows: list[list[Any]]) -> None:
    store = Store(db.connect(":memory:"))
    assert store.is_empty()
    new = store.record(parsed(report_rows), seed=True)
    assert len(new) == 3  # Acme, USRA (three rows, one notice), David's Bridal
    assert store.pending(20) == []
    assert store.counts() == {"seeded": 3}


def test_later_new_notice_becomes_pending_and_groups_rows(report_rows: list[list[Any]]) -> None:
    store = Store(db.connect(":memory:"))
    store.record(parsed(report_rows[:1]), seed=True)
    new = store.record(parsed(report_rows), seed=False)  # same report, more rows
    assert len(new) == 2
    pending = store.pending(20)
    assert [n["company"] for n in pending] == [
        "USRA at ARC",
        "David’s Bridal, LLC",
    ]  # oldest notice first
    usra = pending[0]
    assert usra["rows"] == 3
    assert usra["employees"] == 7
    assert (usra["effective_from"], usra["effective_to"]) == ("2026-12-31", "2027-03-31")


def test_rerecording_the_same_rows_is_a_no_op(report_rows: list[list[Any]]) -> None:
    store = Store(db.connect(":memory:"))
    store.record(parsed(report_rows), seed=True)
    assert store.record(parsed(report_rows), seed=False) == []
    assert store.pending(20) == []


def test_late_row_for_a_posted_notice_is_stored_but_not_reposted(
    report_rows: list[list[Any]],
) -> None:
    store = Store(db.connect(":memory:"))
    store.record(parsed(report_rows[:1]), seed=True)
    store.record(parsed(report_rows[1:3]), seed=False)
    [usra] = store.pending(20)
    store.mark_posted(usra["notice_key"], "123")
    store.record(parsed(report_rows[3:4]), seed=False)  # third USRA row arrives later
    assert store.pending(20) == []
    assert store.notice(usra["notice_key"])["rows"] == 3
    assert store.status(usra["notice_key"])["status_id"] == "123"


def test_failed_posts_retry_then_give_up() -> None:
    store = Store(db.connect(":memory:"))
    store.record(parsed([row("Acme Corp", "2026-11-10", "2027-01-10", 120)]), seed=False)
    [notice] = store.pending(20)
    for attempt in range(1, MAX_ATTEMPTS):
        store.mark_failed(notice["notice_key"], "HTTP 503")
        assert len(store.pending(20)) == 1, f"still retried after attempt {attempt}"
    store.mark_failed(notice["notice_key"], "HTTP 503")
    assert store.pending(20) == []
    status = store.status(notice["notice_key"])
    assert (status["status"], status["attempts"], status["last_error"]) == (
        "failed",
        MAX_ATTEMPTS,
        "HTTP 503",
    )


def test_pending_respects_the_limit(report_rows: list[list[Any]]) -> None:
    store = Store(db.connect(":memory:"))
    store.record(parsed(report_rows), seed=False)
    assert len(store.pending(1)) == 1
