"""Record a simulated social-media post without making a network request."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from omnigent_client.tools import tool


def _artifacts_path() -> str:
    return os.path.join(os.getcwd(), "examples", "content_factory", "artifacts")


@tool
def post_social(slug: str, channel: str) -> dict:
    """Simulate posting a staged social artifact to a channel.

    :param slug: Backlog slug associated with the social post.
    :param channel: Social channel: x or linkedin.
    :returns: A simulated egress record.
    """
    if channel not in ("x", "linkedin"):
        return {"error": "channel must be x or linkedin"}

    artifacts = _artifacts_path()
    social_path = os.path.join(artifacts, "social", f"{slug}-{channel}.md")
    try:
        with open(social_path, encoding="utf-8") as social_file:
            body = social_file.read()
    except OSError as error:
        return {"error": f"Unable to read staged {channel} post for {slug}: {error}"}

    published_directory = os.path.join(artifacts, "published", slug)
    os.makedirs(published_directory, exist_ok=True)
    record_path = os.path.join(published_directory, f"posted-{channel}.json")
    record = {
        "channel": channel,
        "slug": slug,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "body": body,
    }
    with open(record_path, "w", encoding="utf-8", newline="") as record_file:
        json.dump(record, record_file, indent=2)
        record_file.write("\n")
    return {"slug": slug, "channel": channel, "simulated": True, "record": record_path}
