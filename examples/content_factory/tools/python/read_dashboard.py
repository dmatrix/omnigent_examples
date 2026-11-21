"""Read the disk-backed content-factory dashboard state."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from omnigent_client.tools import tool

from read_backlog import _parse_backlog


def _content_factory_path() -> str:
    return os.path.join(os.getcwd(), "examples", "content_factory")


def _article_ceiling() -> int | None:
    """Read the configured article ceiling without adding a YAML dependency."""
    try:
        with open(os.path.join(_content_factory_path(), "config.yaml"), encoding="utf-8") as config_file:
            match = re.search(r"(?m)^\s*max_articles_per_cycle:\s*(\d+)\s*$", config_file.read())
    except OSError:
        return None
    return int(match.group(1)) if match else None


def _existing_names(directory: str) -> list[str]:
    try:
        return sorted(name for name in os.listdir(directory) if os.path.isfile(os.path.join(directory, name)))
    except OSError:
        return []


@tool
def read_dashboard() -> dict:
    """Return a read-only, disk-derived dashboard snapshot.

    :returns: A JSON-serializable dict with ``entries`` in backlog file order.
        Each entry has ``slug``, ``title``, ``status``, and ``artifacts`` with
        booleans ``outline`` and ``draft`` plus lists ``social_variants``,
        ``published_files``, and ``posted_channels``. ``shipped_article_count``
        counts backlog slugs whose published directory contains that slug's
        draft; ``article_ceiling`` is the configured ceiling when readable;
        and ``utc_date`` is today's UTC date.
    """
    root = _content_factory_path()
    try:
        with open(os.path.join(root, "backlog.md"), encoding="utf-8") as backlog_file:
            items = _parse_backlog(backlog_file.read())
    except OSError as error:
        return {"error": f"Unable to read backlog: {error}"}

    artifacts_root = os.path.join(root, "artifacts")
    entries = []
    shipped_article_count = 0
    for item in items:
        slug = item["slug"]
        published_directory = os.path.join(artifacts_root, "published", slug)
        published_files = _existing_names(published_directory)
        social_variants = [
            channel
            for channel in ("x", "linkedin")
            if os.path.isfile(os.path.join(artifacts_root, "social", f"{slug}-{channel}.md"))
        ]
        posted_channels = [
            channel
            for channel in ("x", "linkedin")
            if os.path.isfile(os.path.join(published_directory, f"posted-{channel}.json"))
        ]
        if f"{slug}.md" in published_files:
            shipped_article_count += 1
        entries.append(
            {
                "slug": slug,
                "title": item.get("title", ""),
                "status": item.get("status", ""),
                "artifacts": {
                    "outline": os.path.isfile(os.path.join(artifacts_root, "outlines", f"{slug}.md")),
                    "draft": os.path.isfile(os.path.join(artifacts_root, "drafts", f"{slug}.md")),
                    "social_variants": social_variants,
                    "published_files": published_files,
                    "posted_channels": posted_channels,
                },
            }
        )

    snapshot = {
        "entries": entries,
        "shipped_article_count": shipped_article_count,
        "utc_date": datetime.now(timezone.utc).date().isoformat(),
    }
    ceiling = _article_ceiling()
    if ceiling is not None:
        snapshot["article_ceiling"] = ceiling
    return snapshot
