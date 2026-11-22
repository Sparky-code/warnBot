import sqlite3

from warnbot.app import main, run
from warnbot.tests.conftest import make_report, row


class FakePoster:
    def __init__(self, fail=False):
        self.posts = []
        self.fail = fail

    def __call__(self, text, key):
        if self.fail:
            raise RuntimeError("HTTP 503")
        self.posts.append((text, key))
        return {"id": str(len(self.posts))}


def write(tmp_path, rows, name="report.xlsx"):
    path = tmp_path / name
    path.write_bytes(make_report(rows))
    return path


def test_first_run_seeds_then_only_new_notices_are_posted(tmp_path, report_rows):
    db = tmp_path / "warnbot.db"
    poster = FakePoster()

    first = run(db=db, report_file=write(tmp_path, report_rows[:4]), poster=poster)
    assert first["seeded"] and first["new"] == 2 and poster.posts == []

    second = run(db=db, report_file=write(tmp_path, report_rows), poster=poster)
    assert (second["new"], second["posted"]) == (1, 1)
    [(text, _)] = poster.posts
    assert text.startswith("Closure (permanent): David’s Bridal, LLC")

    third = run(db=db, report_file=write(tmp_path, report_rows), poster=poster)
    assert (third["new"], third["posted"]) == (0, 0)


def test_max_posts_caps_a_run(tmp_path, report_rows):
    db = tmp_path / "warnbot.db"
    run(db=db, report_file=write(tmp_path, report_rows[:1]), poster=FakePoster())
    extra = [row(f"Company {i}", "2026-11-15", "2027-01-15", 10, address=f"{i} Elm St") for i in range(5)]
    poster = FakePoster()
    result = run(db=db, report_file=write(tmp_path, report_rows[:1] + extra), poster=poster, max_posts=2)
    assert result["posted"] == 2
    assert result["status"]["pending"] == 3  # the rest wait for the next run


def test_failed_post_is_recorded_and_retried(tmp_path, report_rows):
    db = tmp_path / "warnbot.db"
    run(db=db, report_file=write(tmp_path, report_rows[:1]), poster=FakePoster())
    failing = run(db=db, report_file=write(tmp_path, report_rows[:2]), poster=FakePoster(fail=True))
    assert failing["failed"] == 1
    retry = run(db=db, report_file=write(tmp_path, report_rows[:2]), poster=FakePoster())
    assert retry["posted"] == 1


def test_dry_run_changes_nothing(tmp_path, report_rows, capsys):
    db = tmp_path / "warnbot.db"
    run(db=db, report_file=write(tmp_path, report_rows[:1]), poster=FakePoster())
    before = sqlite3.connect(db).execute("SELECT COUNT(*) FROM rows").fetchone()[0]

    poster = FakePoster()
    result = run(db=db, report_file=write(tmp_path, report_rows), poster=poster, dry_run=True)
    assert result["new"] == 2 and poster.posts == []  # Acme was seeded by the first run
    assert "would post" in capsys.readouterr().out
    assert sqlite3.connect(db).execute("SELECT COUNT(*) FROM rows").fetchone()[0] == before


def test_dry_run_does_not_create_the_database(tmp_path, report_rows):
    db = tmp_path / "missing.db"
    run(db=db, report_file=write(tmp_path, report_rows), dry_run=True, poster=FakePoster())
    assert not db.exists()


def test_main_returns_nonzero_on_a_bad_report(tmp_path):
    bad = tmp_path / "bad.xlsx"
    bad.write_bytes(b"not a workbook")
    assert main(["--db", str(tmp_path / "w.db"), "--file", str(bad)]) == 1
