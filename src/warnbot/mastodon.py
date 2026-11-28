"""Post a status to Mastodon. Settings: MASTODON_HOST, MASTODON_TOKEN."""

from __future__ import annotations

import os
from typing import Any

import httpx


def post_status(
    text: str, idempotency_key: str | None = None, client: httpx.Client | None = None
) -> dict[str, Any]:
    """Post a status (toot) to the configured Mastodon instance.

    With `idempotency_key`, Mastodon ignores a repeat of the same request for
    an hour, so retrying after a timeout cannot post twice.
    """
    host = os.environ.get("MASTODON_HOST", "").rstrip("/")
    token = os.environ.get("MASTODON_TOKEN", "")
    if not host or not token:
        raise RuntimeError("MASTODON_HOST and MASTODON_TOKEN must be set")
    headers = {"Authorization": f"Bearer {token}"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    http = client or httpx.Client(timeout=30)
    r = http.post(f"{host}/api/v1/statuses", data={"status": text}, headers=headers)
    r.raise_for_status()
    result: dict[str, Any] = r.json()
    return result
