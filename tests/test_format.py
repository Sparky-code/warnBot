from __future__ import annotations

from typing import Any

from warnbot.format import MAX_LENGTH, format_notice


def notice(**overrides: Any) -> dict[str, Any]:
    base = {
        "company": "Example Corp",
        "county": "Santa Clara County",
        "employees": 120,
        "notice_date": "2026-11-14",
        "effective_from": "2027-01-15",
        "effective_to": "2027-01-15",
        "layoff_closure": "Layoff Permanent",
    }
    base.update(overrides)
    return base


def test_typical_notice() -> None:
    assert format_notice(notice()) == (
        "Layoff (permanent): Example Corp\n"
        "Santa Clara County · 120 employees\n"
        "Notice 2026-11-14 · effective 2027-01-15\n"
        "#CAWARN #layoffs"
    )


def test_effective_range_and_closure_and_singular() -> None:
    text = format_notice(
        notice(employees=1, effective_to="2027-03-31", layoff_closure="Closure Permanent")
    )
    assert text.startswith("Closure (permanent): ")
    assert "1 employee\n" in text
    assert "effective 2027-01-15 to 2027-03-31" in text


def test_missing_fields_are_left_out() -> None:
    text = format_notice(
        notice(employees=None, effective_from=None, effective_to=None, layoff_closure="")
    )
    assert (
        text == "WARN notice: Example Corp\nSanta Clara County\nNotice 2026-11-14\n#CAWARN #layoffs"
    )


def test_long_company_names_are_trimmed_to_fit() -> None:
    text = format_notice(notice(company="X" * 2000))
    assert len(text) <= MAX_LENGTH
    assert "…" in text
    assert text.endswith("#CAWARN #layoffs")
