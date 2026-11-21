"""Read content-factory backlog entries from the local Markdown backlog."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from omnigent_client.tools import tool


def _backlog_path() -> str:
    return os.path.join(os.getcwd(), "examples", "content_factory", "backlog.md")


def _content_factory_path() -> str:
    return os.path.join(os.getcwd(), "examples", "content_factory")


def _parse_backlog(content: str) -> list[dict]:
    """Parse the content-factory backlog Markdown in file order."""
    items = []
    for section in re.split(r"(?m)^## ", content)[1:]:
        lines = section.splitlines()
        if not lines:
            continue
        item = {"slug": lines[0].strip(), "sources": []}
        in_sources = False
        for line in lines[1:]:
            if line.startswith("- sources:"):
                in_sources = True
                continue
            if in_sources and line.startswith("  - "):
                item["sources"].append(line[4:].strip())
                continue
            in_sources = False
            match = re.match(r"- (status|title|summary):\s*(.*)$", line)
            if match:
                item[match.group(1)] = match.group(2).strip()
        items.append(item)
    return items


def _article_ceiling() -> int | None:
    """Read the configured ceiling only from publish_gate's YAML argument."""
    try:
        with open(os.path.join(_content_factory_path(), "config.yaml"), encoding="utf-8") as config_file:
            lines = config_file.read().splitlines()
    except OSError:
        return None

    sections = (
        r"guardrails:\s*",
        r"  policies:\s*",
        r"    publish_gate:\s*",
        r"      function:\s*",
        r"        arguments:\s*",
    )
    section_index = 0
    for line in lines:
        if section_index < len(sections):
            if re.fullmatch(sections[section_index], line):
                section_index += 1
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"          max_articles_per_cycle:\s*(\d+)\s*", line)
        return int(match.group(1)) if match else None
    return None


def _existing_names(directory: str) -> list[str]:
    try:
        return sorted(name for name in os.listdir(directory) if os.path.isfile(os.path.join(directory, name)))
    except OSError:
        return []


def _dashboard_snapshot(items: list[dict]) -> dict:
    """Build the read-only all-time artifact view for every backlog entry."""
    artifacts_root = os.path.join(_content_factory_path(), "artifacts")
    entries = []
    published_article_count = 0
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
        # This counts durable article files, not the policy's session-scoped R3
        # admission set. R3 admits a slug after any first successful guarded call.
        if f"{slug}.md" in published_files:
            published_article_count += 1
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
        "published_article_count": published_article_count,
        "utc_date": datetime.now(timezone.utc).date().isoformat(),
    }
    ceiling = _article_ceiling()
    if ceiling is not None:
        snapshot["article_ceiling"] = ceiling
    return snapshot


@tool
def read_backlog(status: str = "READY", limit: int = 1, include_artifacts: bool = False) -> dict:
    """Read backlog entries filtered by status.

    :param status: Backlog status to include.
    :param limit: Maximum number of matching entries to return.
    :param include_artifacts: Return the all-entry disk dashboard instead of a
        filtered backlog result. The dashboard has ``entries`` in file order,
        ``published_article_count`` based on durable ``<slug>.md`` files,
        optional ``article_ceiling``, and ``utc_date``. Its count deliberately
        differs from the session-scoped publish-gate ceiling state.
    :returns: Matching entries and counts by status.
    """
    try:
        with open(_backlog_path(), encoding="utf-8") as backlog_file:
            items = _parse_backlog(backlog_file.read())
    except OSError as error:
        return {"error": f"Unable to read backlog: {error}"}

    if include_artifacts:
        return _dashboard_snapshot(items)

    counts = {}
    for item in items:
        item_status = item.get("status", "")
        counts[item_status] = counts.get(item_status, 0) + 1

    return {
        "items": [item for item in items if item.get("status") == status][:limit],
        "counts": counts,
    }
