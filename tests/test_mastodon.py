from __future__ import annotations

import httpx
import pytest

from warnbot.mastodon import post_status


def test_posts_with_token_and_idempotency_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MASTODON_HOST", "https://mastodon.example/")
    monkeypatch.setenv("MASTODON_TOKEN", "secret")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id": "42"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert post_status("hello", idempotency_key="k1", client=client) == {"id": "42"}
    [req] = seen
    assert str(req.url) == "https://mastodon.example/api/v1/statuses"
    assert req.headers["Authorization"] == "Bearer secret"
    assert req.headers["Idempotency-Key"] == "k1"
    assert req.content == b"status=hello"


def test_needs_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MASTODON_HOST", raising=False)
    with pytest.raises(RuntimeError, match="MASTODON_HOST"):
        post_status("hello")
