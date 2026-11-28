from __future__ import annotations

import datetime as dt
import io
from typing import Any

import pytest
from openpyxl import Workbook

HEADERS = [
    "County/Parish",
    "Notice\nDate",
    "Processed\nDate",
    "Effective \nDate",
    "Company",
    "Layoff/\nClosure",
    "No. Of\nEmployees",
    "Address",
    "Related Industry",
]


def serial(day: str) -> int:
    """Excel serial number for an ISO date, as the EDD file stores dates."""
    return (dt.date.fromisoformat(day) - dt.date(1899, 12, 30)).days


def make_report(
    rows: list[list[Any]],
    *,
    sheet: str = "Detailed WARN Report ",
    headers: list[str] = HEADERS,
    total: bool = True,
) -> bytes:
    """An xlsx shaped like the EDD report: index sheet, title row, header row, data, total row."""
    wb = Workbook()
    index = wb.worksheets[0]
    index.title = "Index"
    index.append(["This worksheet contains several sheets"])
    ws = wb.create_sheet(sheet)
    ws.append(["WARN REPORT - 07/01/26 to 11/20/26"])
    ws.append(headers)
    for r in rows:
        ws.append(r)
    if total:
        ws.append(
            [
                None,
                None,
                None,
                None,
                "Total",
                None,
                sum(r[6] for r in rows if isinstance(r[6], int)),
            ]
        )
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def row(
    company: str,
    notice: str,
    effective: str,
    employees: int,
    county: str = "Santa Clara County",
    address: str = "1 Main St  San Jose CA 95110",
    kind: str = "Layoff Permanent",
    industry: str = "51 Information",
) -> list[Any]:
    return [
        county,
        serial(notice),
        serial(notice),
        serial(effective),
        company,
        kind,
        employees,
        address,
        industry,
    ]


@pytest.fixture
def report_rows() -> list[list[Any]]:
    return [
        row("Acme Corp", "2026-11-10", "2027-01-10", 120),
        # One filing spread over three rows (different effective dates).
        row(
            "USRA at ARC",
            "2026-11-12",
            "2027-01-31",
            4,
            address="Moffett Field  Mountain View CA 94043",
        ),
        row(
            "USRA at ARC",
            "2026-11-12",
            "2027-03-31",
            2,
            address="Moffett Field  Mountain View CA 94043",
        ),
        row(
            "USRA at ARC",
            "2026-11-12",
            "2026-12-31",
            1,
            address="Moffett Field  Mountain View CA 94043",
        ),
        row(
            "David&rsquo;s Bridal, LLC",
            "2026-11-14",
            "2027-01-14",
            29,
            county="Contra Costa County",
            address="1212 Fitzgerald Dr Pinole CA 94564",
            kind="Closure Permanent",
            industry="44-45 Retail Trade",
        ),
    ]
