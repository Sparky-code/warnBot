"""Find and download California's current WARN report from the EDD site.

The report's file name changes between fiscal years (warn_report.xlsx became
warn_report1.xlsx), so the link is read from the EDD WARN page each run, with
the last known URL as a fallback.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

import httpx

log = logging.getLogger(__name__)

WARN_PAGE = "https://edd.ca.gov/en/jobs_and_training/Layoff_Services_WARN"
FALLBACK_URL = "https://edd.ca.gov/siteassets/files/jobs_and_training/warn/warn_report1.xlsx"
USER_AGENT = "warnBot/0.3 (+https://github.com/Sparky-code/warnBot)"
TIMEOUT = 60

_REPORT_LINK = re.compile(r'href="([^"]*warn_report[^"]*\.xlsx)"', re.IGNORECASE)


def find_report_url(client: httpx.Client | None = None) -> str:
    """The current report's URL, read from the EDD WARN page."""
    http = client or httpx.Client(follow_redirects=True)
    try:
        page = http.get(WARN_PAGE, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        page.raise_for_status()
        match = _REPORT_LINK.search(page.text)
        if match:
            return urljoin(WARN_PAGE, str(match.group(1)))
        log.warning("No WARN report link on %s; using the fallback URL", WARN_PAGE)
    except httpx.HTTPError as exc:
        log.warning("Could not read %s (%s); using the fallback URL", WARN_PAGE, exc)
    return FALLBACK_URL


def download(url: str, client: httpx.Client | None = None) -> bytes:
    """Download the report and return its bytes."""
    http = client or httpx.Client(follow_redirects=True)
    res = http.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    res.raise_for_status()
    return res.content
