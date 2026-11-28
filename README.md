# warnBot

A bot that watches California WARN Act layoff notices and posts new
announcements to Mastodon.

## How it works

Each run of `warnbot run`:

1. **Finds the report** (`src/warnbot/fetch.py`): reads the link to the
   current report from the EDD WARN page. The file name changes between fiscal
   years (`warn_report.xlsx` became `warn_report1.xlsx`). The last known URL is
   the fallback.
2. **Parses it** (`parse.py`): reads the "Detailed WARN Report" sheet, finding
   columns by header name so added or renamed columns don't break it. It skips
   the title and total rows and decodes HTML entities in names.
3. **Records new rows** (`store.py`) in a local SQLite file,
   `data/warnbot.db`. Rows are grouped into notices by company, address and
   notice date, because one filing can span many rows. **The first run only
   seeds:** everything already in the report is marked as seen and nothing is
   posted.
4. **Posts new notices** (`format.py`, `mastodon.py`): one Mastodon post per
   notice, oldest first, at most 20 per run (`--max`). Each post sends an
   `Idempotency-Key` so a retry can't post twice. A failed post is retried on
   later runs, up to 5 attempts, and fails the run so the alert fires.

```
Layoff (permanent): Example Corp
Santa Clara County · 120 employees
Notice 2026-11-14 · effective 2027-01-15
#CAWARN #layoffs
```

The job runner (`job.py`) holds a lock so runs can't overlap, records every
run in the database (`warnbot status`), and sends an ntfy push notification
when a run fails. `data/warn_report_sample.csv` is a sample of older (2022)
report data.

## Status

Revived 2026-10-19 after being dormant since 2023. On 2026-11-22 the Google
Sheet store was replaced with SQLite and the pipeline was finished. On
2026-11-28 it moved to the standard Python CLI shape (uv, Typer, httpx, run
lock and run records, launchd schedule). A live dry run against the EDD report
seeds about 590 notices. No Google credentials are needed any more.

## Roadmap

- [x] Replace the Google Sheet with a local SQLite store
- [x] Find the current report automatically; parse by header name
- [x] Find new notices, format one post per notice, post and record them
- [x] Run lock, run records, failure alerts, launchd schedule
- [ ] Delete the old Google service account in Google Cloud (its key was
      committed in this repo's history; nothing uses it now)
- [ ] First real post: one `--max 1` run with the Mastodon token
- [ ] Install the schedule (`ops/launchd/install.sh`)

## Setup

Needs [uv](https://docs.astral.sh/uv/) (it installs Python 3.14 itself) and lefthook.

```bash
uv sync
lefthook install
cp .env.example .env   # fill in the Mastodon host and token
```

Settings come only from the environment; `.env` is never committed.

## Usage

```bash
uv run --env-file .env warnbot run --dry-run   # show what would be posted; changes no notices
uv run --env-file .env warnbot run             # first run seeds; later runs post new notices
uv run --env-file .env warnbot run --max 1     # cap the posts for this run
uv run --env-file .env warnbot run --file report.xlsx   # use a local report
uv run --env-file .env warnbot status          # notice counts and recent runs
```

### Schedule

`ops/launchd/install.sh` installs a launchd agent that runs the job daily at
06:00 (edit the plist to change the time). Logs go to
`~/Library/Logs/warnbot/`. If `NTFY_URL` is set, a failed run sends a push
notification.

## Development

```bash
uv run pytest               # tests (network tests: uv run pytest -m live)
uv run mypy                 # type check
uv run ruff check           # lint
uv run ruff format          # format
```

Hooks run format and lint on commit, and typecheck and tests on push. Commit
messages follow `type(scope): Imperative subject` (see `CLAUDE.md`).
