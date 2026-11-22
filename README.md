# warnBot

A bot that watches California WARN Act layoff notices and posts new
announcements to Mastodon.

## How it works

Each run of `python -m warnbot.app`:

1. **Finds the report** (`warnbot/fetch.py`): reads the link to the current
   report from the EDD WARN page. The file name changes between fiscal years
   (`warn_report.xlsx` became `warn_report1.xlsx`). The last known URL is the
   fallback.
2. **Parses it** (`warnbot/parse.py`): reads the "Detailed WARN Report" sheet,
   finding columns by header name so added or renamed columns don't break it.
   It skips the title and total rows and decodes HTML entities in names.
3. **Records new rows** (`warnbot/store.py`) in a local SQLite file,
   `data/warnbot.db`. Rows are grouped into notices by company, address and
   notice date, because one filing can span many rows. **The first run only
   seeds:** everything already in the report is marked as seen and nothing is
   posted.
4. **Posts new notices** (`warnbot/format.py`, `warnbot/create_msg.py`): one
   Mastodon post per notice, oldest first, at most 20 per run. Each post sends
   an `Idempotency-Key` so a retry can't post twice. A failed post is retried
   on later runs, up to 5 attempts.

```
Layoff (permanent): Example Corp
Santa Clara County · 120 employees
Notice 2026-11-14 · effective 2027-01-15
#CAWARN #layoffs
```

`data/warn_report_sample.csv` is a sample of older (2022) report data.

## Status

Revived 2026-10-19 after being dormant since 2023. On 2026-11-22 the Google
Sheet store was replaced with SQLite and the pipeline was finished. A live dry
run against the EDD report seeds about 590 notices and finds new ones
correctly. No Google credentials are needed any more.

## Roadmap

- [x] Replace the Google Sheet with a local SQLite store
- [x] Find the current report automatically; parse by header name
- [x] Find new notices, format one post per notice, post and record them
- [ ] Delete the old Google service account in Google Cloud (its key was
      committed in this repo's history; nothing uses it now)
- [ ] First real post: one `--max-posts 1` run with the Mastodon token
- [ ] Schedule a regular run (cron or launchd)

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in the Mastodon host and token
```

The app reads `MASTODON_HOST` and `MASTODON_TOKEN` from the environment, so
export them before running (for example `set -a; source .env; set +a`).

```bash
python -m warnbot.app --dry-run        # show what would be posted; changes nothing
python -m warnbot.app                  # first run seeds; later runs post new notices
python -m warnbot.app --max-posts 1    # cap the posts for this run
python -m warnbot.app --file report.xlsx   # use a local report instead of downloading
pytest warnbot/tests
```
