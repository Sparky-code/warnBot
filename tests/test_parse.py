from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import HEADERS, make_report, row
from warnbot.parse import parse_report


def test_parses_rows_and_skips_title_and_total(report_rows: list[list[Any]]) -> None:
    rows = parse_report(make_report(report_rows))
    assert len(rows) == 5  # title row and total row skipped
    assert rows[0] == {
        "county": "Santa Clara County",
        "notice_date": "2026-11-10",
        "processed_date": "2026-11-10",
        "effective_date": "2027-01-10",
        "company": "Acme Corp",
        "layoff_closure": "Layoff Permanent",
        "employees": 120,
        "address": "1 Main St San Jose CA 95110",  # whitespace collapsed
        "industry": "51 Information",
    }


def test_decodes_html_entities(report_rows: list[list[Any]]) -> None:
    rows = parse_report(make_report(report_rows))
    assert rows[-1]["company"] == "David’s Bridal, LLC"


def test_older_layout_without_industry_and_with_received_date() -> None:
    headers = [h for h in HEADERS if h != "Related Industry"]
    headers[2] = "Received\nDate"
    data = [row("Acme Corp", "2024-04-11", "2024-06-10", 6)[:-1]]
    [parsed] = parse_report(make_report(data, headers=headers))
    assert parsed["processed_date"] == "2024-04-11"
    assert parsed["industry"] is None


def test_reordered_columns_are_found_by_name() -> None:
    headers = ["Company", "Address", "No. Of\nEmployees", "County/Parish", "Notice\nDate"]
    data = [["Acme Corp", "1 Main St", 12, "Alameda County", "2026-11-10"]]
    wb = make_report(data, headers=headers, total=False)
    [parsed] = parse_report(wb)
    assert (parsed["company"], parsed["employees"], parsed["county"], parsed["notice_date"]) == (
        "Acme Corp",
        12,
        "Alameda County",
        "2026-11-10",
    )


def test_missing_sheet_or_header_is_an_error(report_rows: list[list[Any]]) -> None:
    with pytest.raises(ValueError, match="Detailed WARN Report"):
        parse_report(make_report(report_rows, sheet="Something Else"))
    with pytest.raises(ValueError, match="header row"):
        parse_report(make_report([], headers=["Nothing", "Useful"], total=False))
