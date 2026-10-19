import os

import requests

MASTODON_HOST = os.environ.get("MASTODON_HOST", "").rstrip("/")
MASTODON_TOKEN = os.environ.get("MASTODON_TOKEN", "")


def post_status(text: str) -> dict:
    """Post a status (toot) to the configured Mastodon instance."""
    if not MASTODON_HOST or not MASTODON_TOKEN:
        raise RuntimeError("MASTODON_HOST and MASTODON_TOKEN must be set")
    r = requests.post(
        f"{MASTODON_HOST}/api/v1/statuses",
        data={"status": text},
        headers={"Authorization": f"Bearer {MASTODON_TOKEN}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    print(post_status("testing 1 2, 1 2"))
