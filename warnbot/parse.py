"""Parse the EDD WARN report workbook into plain row dicts.

The data lives on the sheet whose name starts with "Detailed WARN Report".
A title row sits above the header row, headers contain line breaks
("Notice\\nDate"), columns get added and renamed over time ("Received Date"
became "Processed Date", "Related Industry" appeared), dates may be Excel
serial numbers, and the sheet ends with non-data rows such as totals. Columns
are therefore found by header name, and rows without a company and a valid
notice date are skipped.
"""
from __future__ import annotations

import datetime as dt
import html
import io
import re
from typing import Any

from openpyxl import load_workbook

# Normalized header text -> field name. The first matching alias wins.
FIELDS: dict[str, tuple[str, ...]] = {
    "county": ("county/parish", "county"),
    "notice_date": ("notice date",),
    "processed_date": ("processed date", "received date"),
    "effective_date": ("effective date",),
    "company": ("company",),
    "layoff_closure": ("layoff/closure", "layoff/ closure"),
    "employees": ("no. of employees", "number of employees"),
    "address": ("address",),
    "industry": ("related industry",),
}

EXCEL_EPOCH = dt.date(1899, 12, 30)


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _text(value: Any) -> str:
    # Some cells carry HTML entities from the EDD's tooling ("David&rsquo;s Bridal").
    return re.sub(r"\s+", " ", html.unescape(str(value))).strip() if value is not None else ""


def _date(value: Any) -> str | None:
    """ISO date from a datetime, a date, an Excel serial or a date string."""
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, (int, float)) and 20000 < value < 80000:  # 1954 to 2119
        return (EXCEL_EPOCH + dt.timedelta(days=int(value))).isoformat()
    if isinstance(value, str):
        s = value.strip()
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d %H:%M:%S"):
            try:
                return dt.datetime.strptime(s, fmt).date().isoformat()
            except ValueError:
                pass
    return None


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    m = re.fullmatch(r"\s*(\d[\d,]*)\s*", str(value or ""))
    return int(m.group(1).replace(",", "")) if m else None


def _header_map(row: tuple[Any, ...]) -> dict[str, int] | None:
    """Column index per field if `row` is the header row, else None."""
    names = [_norm(c) for c in row]
    if "company" not in names or not any(n.startswith("notice") for n in names):
        return None
    cols: dict[str, int] = {}
    for field, aliases in FIELDS.items():
        for i, name in enumerate(names):
            if name in aliases:
                cols[field] = i
                break
    return cols


def parse_report(data: bytes) -> list[dict[str, Any]]:
    """Rows of the detailed WARN report, as dicts with the keys of FIELDS."""
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    sheet = next((ws for ws in wb.worksheets if ws.title.strip().lower().startswith("detailed warn report")), None)
    if sheet is None:
        raise ValueError(f"No 'Detailed WARN Report' sheet (sheets: {wb.sheetnames})")

    cols: dict[str, int] | None = None
    out: list[dict[str, Any]] = []
    for row in sheet.iter_rows(values_only=True):
        if cols is None:
            cols = _header_map(row)
            continue

        def get(field: str) -> Any:
            i = cols.get(field)  # type: ignore[union-attr]
            return row[i] if i is not None and i < len(row) else None

        company = _text(get("company"))
        notice_date = _date(get("notice_date"))
        if not company or not notice_date:
            continue  # blank, total and footer rows
        out.append(
            {
                "county": _text(get("county")),
                "notice_date": notice_date,
                "processed_date": _date(get("processed_date")),
                "effective_date": _date(get("effective_date")),
                "company": company,
                "layoff_closure": _text(get("layoff_closure")),
                "employees": _int(get("employees")),
                "address": _text(get("address")),
                "industry": _text(get("industry")) or None,
            }
        )
    wb.close()
    if cols is None:
        raise ValueError("No header row with 'Company' and 'Notice Date' found")
    return out
