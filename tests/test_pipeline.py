from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import make_report, row
from warnbot import db
from warnbot.pipeline import PostsFailedError, run


class FakePoster:
    def __init__(self, fail: bool = False) -> None:
        self.posts: list[tuple[str, str]] = []
        self.fail = fail

    def __call__(self, text: str, key: str) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("HTTP 503")
        self.posts.append((text, key))
        return {"id": str(len(self.posts))}


def write(tmp_path: Path, rows: list[list[Any]], name: str = "report.xlsx") -> Path:
    path = tmp_path / name
    path.write_bytes(make_report(rows))
    return path


def quiet(_: str) -> None:
    pass


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    return db.connect(tmp_path / "warnbot.db")


def test_first_run_seeds_then_only_new_notices_are_posted(
    conn: sqlite3.Connection, tmp_path: Path, report_rows: list[list[Any]]
) -> None:
    poster = FakePoster()

    first = run(conn, report_file=write(tmp_path, report_rows[:4]), poster=poster, log=quiet)
    assert first["seeded"] and first["new"] == 2 and poster.posts == []

    second = run(conn, report_file=write(tmp_path, report_rows), poster=poster, log=quiet)
    assert (second["new"], second["posted"]) == (1, 1)
    [(text, _)] = poster.posts
    assert text.startswith("Closure (permanent): David’s Bridal, LLC")

    third = run(conn, report_file=write(tmp_path, report_rows), poster=poster, log=quiet)
    assert (third["new"], third["posted"]) == (0, 0)


def test_max_posts_caps_a_run(
    conn: sqlite3.Connection, tmp_path: Path, report_rows: list[list[Any]]
) -> None:
    run(conn, report_file=write(tmp_path, report_rows[:1]), poster=FakePoster(), log=quiet)
    extra = [
        row(f"Company {i}", "2026-11-15", "2027-01-15", 10, address=f"{i} Elm St") for i in range(5)
    ]
    poster = FakePoster()
    report = write(tmp_path, report_rows[:1] + extra)
    result = run(conn, report_file=report, poster=poster, max_posts=2, log=quiet)
    assert result["posted"] == 2
    assert result["status"]["pending"] == 3  # the rest wait for the next run


def test_failed_post_raises_after_the_run_and_is_retried(
    conn: sqlite3.Connection, tmp_path: Path, report_rows: list[list[Any]]
) -> None:
    run(conn, report_file=write(tmp_path, report_rows[:1]), poster=FakePoster(), log=quiet)
    with pytest.raises(PostsFailedError, match="1 post"):
        run(
            conn,
            report_file=write(tmp_path, report_rows[:2]),
            poster=FakePoster(fail=True),
            log=quiet,
        )
    retry = run(conn, report_file=write(tmp_path, report_rows[:2]), poster=FakePoster(), log=quiet)
    assert retry["posted"] == 1


def test_dry_run_changes_no_notice_state(
    conn: sqlite3.Connection, tmp_path: Path, report_rows: list[list[Any]]
) -> None:
    run(conn, report_file=write(tmp_path, report_rows[:1]), poster=FakePoster(), log=quiet)
    before = conn.execute("SELECT COUNT(*) FROM rows").fetchone()[0]

    poster = FakePoster()
    lines: list[str] = []
    report = write(tmp_path, report_rows)
    result = run(conn, report_file=report, poster=poster, dry_run=True, log=lines.append)
    assert result["new"] == 2 and poster.posts == []  # Acme was seeded by the first run
    assert any("would post" in line for line in lines)
    assert conn.execute("SELECT COUNT(*) FROM rows").fetchone()[0] == before
