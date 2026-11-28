# warnbot

Posts new California WARN Act layoff notices to Mastodon.

## Commands

- Install: `uv sync`
- Test: `uv run pytest` (network tests: `-m live`) · Types: `uv run mypy` · Lint/format: `uv run ruff check` / `uv run ruff format`
- Run: `uv run --env-file .env warnbot run --dry-run`

## Layout

- `src/warnbot/cli.py` commands (Typer) · `job.py` run lock, run record, failure alert
- `db.py` SQLite connection and the numbered migration list · `data/` local SQLite (git-ignored)
- `pipeline.py` one run: `fetch.py` (find + download the EDD report) → `parse.py` → `store.py` (rows, notices, statuses) → `format.py` → `mastodon.py`
- `tests/` pytest (`conftest.py` builds EDD-shaped workbooks; `test_live.py` hits the real EDD site, never posts) · `ops/launchd/` schedule

## Rules

- Commits: `type(scope)!: Imperative subject` (feat, fix, refactor, docs, test, chore, build, ci), at most 72 characters, optional body saying why. No Co-Authored-By trailers or session IDs. The commit-msg hook enforces this.
- Settings come from environment variables only (`.env`, never committed; keep `.env.example` current).
- New dependencies with `uv add` (dev tools: `uv add --dev`). Keep `uv.lock` committed.
- Schema changes go through a new numbered migration, never ad-hoc changes.
- Jobs are safe to re-run, hold the run lock, honour `--dry-run` and the per-run cap for anything that posts or sends, record each run, and exit non-zero on failure.
