"""Talks to the EDD site; run with `uv run pytest -m live`. Never posts."""

from __future__ import annotations

import pytest

from warnbot import fetch
from warnbot.parse import parse_report

pytestmark = pytest.mark.live


def test_finds_downloads_and_parses_the_current_report() -> None:
    url = fetch.find_report_url()
    assert url.endswith(".xlsx")
    rows = parse_report(fetch.download(url))
    assert len(rows) > 10
    assert all(r["company"] and r["notice_date"] for r in rows)
