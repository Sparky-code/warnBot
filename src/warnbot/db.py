"""SQLite state: one file, schema managed by a numbered migration list.

Each entry in MIGRATIONS runs once, in order; PRAGMA user_version records how
many have been applied. To change the schema, append a new entry; never edit
an old one.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_PATH = Path("data/warnbot.db")

MIGRATIONS: list[str] = [
    # 1: job runs
    """
    CREATE TABLE runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job TEXT NOT NULL,
        started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
        finished_at TEXT,
        ok INTEGER,
        dry_run INTEGER NOT NULL DEFAULT 0,
        detail TEXT
    );
    """,
    # 2: report rows and the notices they group into (see store.py). IF NOT
    # EXISTS adopts a database made before migrations were numbered.
    """
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
    """,
]


def db_path() -> Path:
    return Path(os.environ.get("WARNBOT_DB", DEFAULT_PATH))


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """Open the database (creating it and its folder) and apply pending migrations."""
    target = Path(path) if path is not None else db_path()
    if str(target) != ":memory:":
        target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, autocommit=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> int:
    """Apply migrations newer than the database's user_version; return the new version."""
    (version,) = conn.execute("PRAGMA user_version").fetchone()
    for number, sql in enumerate(MIGRATIONS[version:], start=version + 1):
        conn.executescript(sql)
        conn.execute(f"PRAGMA user_version = {number}")
        conn.commit()
    return len(MIGRATIONS)
