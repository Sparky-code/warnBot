"""Turn a WARN notice into a Mastodon post."""

from __future__ import annotations

from typing import Any

MAX_LENGTH = 500  # Mastodon's default status limit
TAGS = "#CAWARN #layoffs"


def _kind(layoff_closure: str | None) -> str:
    """'Layoff Permanent' -> 'Layoff (permanent)'; unknown text passes through."""
    words = (layoff_closure or "").split()
    if not words:
        return "WARN notice"
    head, rest = words[0].capitalize(), " ".join(words[1:]).lower()
    return f"{head} ({rest})" if rest else head


def _effective(notice: dict[str, Any]) -> str | None:
    start, end = notice.get("effective_from"), notice.get("effective_to")
    if not start:
        return None
    return f"effective {start}" if start == end or not end else f"effective {start} to {end}"


def format_notice(notice: dict[str, Any]) -> str:
    """A post of at most MAX_LENGTH characters describing one notice."""
    employees = notice.get("employees")
    people = (
        f"{employees} employee{'s' if employees != 1 else ''}" if employees is not None else None
    )
    where = " · ".join(p for p in (notice.get("county"), people) if p)
    when = " · ".join(p for p in (f"Notice {notice['notice_date']}", _effective(notice)) if p)
    tail = "\n".join(p for p in (where, when, TAGS) if p)

    kind = _kind(notice.get("layoff_closure"))
    company = notice.get("company") or "Unknown company"
    # The company name is the only free-length part; trim it to fit.
    room = MAX_LENGTH - len(tail) - len(kind) - len(": ") - 1
    if len(company) > room:
        company = company[: max(1, room - 1)].rstrip() + "…"
    return f"{kind}: {company}\n{tail}"
