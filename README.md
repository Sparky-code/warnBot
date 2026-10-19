# warnBot

A bot that watches California WARN Act layoff notices and posts new
announcements to Mastodon.

## How it works

1. `warnbot/app.py` downloads the current WARN report spreadsheet from the
   California EDD site and converts it to CSV in a temp folder.
2. `warnbot/sheets_ctrl.py` reads the previously seen records from a Google
   Sheet ("Warn Data - Current") via a service account and filters to the
   last week of notices.
3. The new rows are diffed against the sheet, formatted into messages, and
   `warnbot/create_msg.py` posts them to a Mastodon instance using the
   statuses API.

`data/warn_report_sample.csv` is a sample of the downloaded data.

## Status

Revived 2026-10-19 after being dormant since 2023. The download step and the
Mastodon poster work; the sheet-reading module runs top to bottom as a script
and still needs wrapping in functions. The diff, message formatting, and
posting loop in `app.py` are stubbed.

## Roadmap

- [ ] Rotate the Google service-account key that was previously committed
- [ ] Wrap `sheets_ctrl.py` in functions (`load_seen`, `recent`, `stage`)
- [ ] Diff the fresh download against the sheet to find new notices
- [ ] Format one message per notice (company, county, employees, date)
- [ ] Post new notices and record them back to the sheet
- [ ] Schedule a weekly run

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in key path and Mastodon values
```

Run with `python -m warnbot.app`.
