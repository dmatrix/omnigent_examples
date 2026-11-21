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


# Key path from the top of config.yaml down to publish_gate's arguments. Walked
# one level at a time so the ceiling is read from publish_gate's own argument
# and nowhere else.
_CEILING_PATH = ("guardrails", "policies", "publish_gate", "function", "arguments")


def _child_lines(block: list[str], key: str) -> list[str] | None:
    """Return the lines nested under mapping entry *key* within *block*.

    Reads the key structure by indentation only -- no values are interpreted.
    The block's own level is the indent of its first content line; siblings sit
    at that indent, children are the more-indented lines that follow a matched
    key. Blank and comment lines are carried through rather than ending a block,
    so a commented argument is still found.

    Scoping, not searching, is the point: a key is matched only at this level,
    so `max_articles_per_cycle` inside a `prompt:` block scalar, or under a
    policy that merely resembles `publish_gate`, is never reached.

    :param block: Lines of one YAML mapping block.
    :param key: The mapping key to descend into.
    :returns: The child lines, or ``None`` when *key* is absent at this level.
    """
    level = None
    for index, line in enumerate(block):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if level is None:
            level = indent
        if indent > level:
            continue
        if indent < level:
            break
        if line.strip().split(":", 1)[0].strip() != key:
            continue
        children = []
        for child in block[index + 1 :]:
            if not child.strip() or child.lstrip().startswith("#"):
                children.append(child)
                continue
            if len(child) - len(child.lstrip()) <= indent:
                break
            children.append(child)
        return children
    return None


def _article_ceiling() -> int | None:
    """Read the ceiling from publish_gate's own ``max_articles_per_cycle``.

    Descends `_CEILING_PATH` by indentation rather than scanning config.yaml as
    an ordered line sequence, so adding or reordering sibling policies cannot
    silently drop the dashboard's ceiling.

    Omits rather than guesses on every failure mode, as before: an unreadable
    config, a missing or renamed `publish_gate`, a non-integer value, and a
    value with a trailing comment all return ``None``.

    :returns: The configured ceiling, or ``None`` when it cannot be read
        unambiguously.
    """
    try:
        with open(os.path.join(_content_factory_path(), "config.yaml"), encoding="utf-8") as config_file:
            block: list[str] | None = config_file.read().splitlines()
    except OSError:
        return None

    for key in _CEILING_PATH:
        if block is None:
            return None
        block = _child_lines(block, key)
    if block is None:
        return None

    for line in block:
        match = re.fullmatch(r"\s*max_articles_per_cycle:\s*(\d+)\s*", line)
        if match:
            return int(match.group(1))
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
