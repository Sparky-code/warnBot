"""Local state in SQLite: which WARN rows have been seen and which notices posted.

Replaces the Google Sheet the bot used to read and write, so no Google
credentials are needed.

A *row* is one line of the EDD report. A *notice* is one filing, which can
span several rows (one company filed 17 rows with different effective dates
for a single notice); rows are grouped into notices by company, address and
notice date, and the bot posts once per notice.

Notice status:
  seeded   already in the report on the first run; never posted
  pending  new; waiting to be posted
  posted   posted to Mastodon
  failed   posting failed MAX_ATTEMPTS times; left alone
"""
from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3
from pathlib import Path
from typing import Any, Iterable

MAX_ATTEMPTS = 5

ROW_FIELDS = (
    "county",
    "notice_date",
    "processed_date",
    "effective_date",
    "company",
    "layoff_closure",
    "employees",
    "address",
    "industry",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS rows (
  row_key        TEXT PRIMARY KEY,
  notice_key     TEXT NOT NULL,
  county         TEXT,
  notice_date    TEXT NOT NULL,
  processed_date TEXT,
  effective_date TEXT,
  company        TEXT NOT NULL,
  layoff_closure TEXT,
  employees      INTEGER,
  address        TEXT,
  industry       TEXT,
  first_seen     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS rows_notice ON rows (notice_key);
CREATE TABLE IF NOT EXISTS notices (
  notice_key  TEXT PRIMARY KEY,
  status      TEXT NOT NULL CHECK (status IN ('seeded', 'pending', 'posted', 'failed')),
  first_seen  TEXT NOT NULL,
  status_id   TEXT,
  posted_at   TEXT,
  attempts    INTEGER NOT NULL DEFAULT 0,
  last_error  TEXT
);
"""


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _sha(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(_norm(p) for p in parts).encode()).hexdigest()


def row_key(row: dict[str, Any]) -> str:
    return _sha(*(row.get(f) for f in ROW_FIELDS))


def notice_key(row: dict[str, Any]) -> str:
    return _sha(row.get("company"), row.get("address"), row.get("notice_date"))


class Store:
    def __init__(self, path: str | Path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    def is_empty(self) -> bool:
        return self.db.execute("SELECT 1 FROM rows LIMIT 1").fetchone() is None

    def record(self, rows: Iterable[dict[str, Any]], seed: bool) -> list[str]:
        """Store rows not seen before. Returns the keys of notices seen for the first time.

        New notices are 'seeded' when `seed` is true, otherwise 'pending'. A new
        row for a notice already known (pending, posted, ...) is stored but does
        not change the notice's status, so a posted notice is never reposted.
        """
        now = _now()
        status = "seeded" if seed else "pending"
        new_notices: list[str] = []
        with self.db:
            for row in rows:
                nk = notice_key(row)
                self.db.execute(
                    f"INSERT OR IGNORE INTO rows (row_key, notice_key, {', '.join(ROW_FIELDS)}, first_seen) "
                    f"VALUES (?, ?, {', '.join('?' for _ in ROW_FIELDS)}, ?)",
                    (row_key(row), nk, *(row.get(f) for f in ROW_FIELDS), now),
                )
                cur = self.db.execute(
                    "INSERT OR IGNORE INTO notices (notice_key, status, first_seen) VALUES (?, ?, ?)",
                    (nk, status, now),
                )
                if cur.rowcount:
                    new_notices.append(nk)
        return new_notices

    def pending(self, limit: int) -> list[dict[str, Any]]:
        """Notices waiting to be posted, oldest notice date first, with their rows aggregated."""
        keys = [
            r["notice_key"]
            for r in self.db.execute(
                """SELECT n.notice_key FROM notices n JOIN rows r USING (notice_key)
                   WHERE n.status = 'pending'
                   GROUP BY n.notice_key ORDER BY MIN(r.notice_date), MIN(r.first_seen) LIMIT ?""",
                (limit,),
            )
        ]
        return [self.notice(k) for k in keys]

    def notice(self, key: str) -> dict[str, Any]:
        rows = [dict(r) for r in self.db.execute("SELECT * FROM rows WHERE notice_key = ? ORDER BY effective_date", (key,))]
        if not rows:
            raise KeyError(key)
        first = rows[0]
        effective = sorted({r["effective_date"] for r in rows if r["effective_date"]})
        known = [r["employees"] for r in rows if r["employees"] is not None]
        return {
            "notice_key": key,
            "company": first["company"],
            "address": first["address"],
            "county": first["county"],
            "notice_date": first["notice_date"],
            "layoff_closure": first["layoff_closure"],
            "industry": first["industry"],
            "employees": sum(known) if known else None,
            "effective_from": effective[0] if effective else None,
            "effective_to": effective[-1] if effective else None,
            "rows": len(rows),
        }

    def status(self, key: str) -> dict[str, Any]:
        r = self.db.execute("SELECT * FROM notices WHERE notice_key = ?", (key,)).fetchone()
        if r is None:
            raise KeyError(key)
        return dict(r)

    def mark_posted(self, key: str, status_id: str | None) -> None:
        with self.db:
            self.db.execute(
                "UPDATE notices SET status = 'posted', status_id = ?, posted_at = ?, last_error = NULL WHERE notice_key = ?",
                (status_id, _now(), key),
            )

    def mark_failed(self, key: str, error: str) -> None:
        """Count a failed attempt; give up (status 'failed') after MAX_ATTEMPTS."""
        with self.db:
            self.db.execute(
                """UPDATE notices SET attempts = attempts + 1, last_error = ?,
                   status = CASE WHEN attempts + 1 >= ? THEN 'failed' ELSE status END
                   WHERE notice_key = ?""",
                (error[:500], MAX_ATTEMPTS, key),
            )

    def counts(self) -> dict[str, int]:
        return {r["status"]: r["n"] for r in self.db.execute("SELECT status, COUNT(*) AS n FROM notices GROUP BY status")}
