"""Read content-factory backlog entries from the local Markdown backlog."""

from __future__ import annotations

import os
import re

from omnigent_client.tools import tool


def _backlog_path() -> str:
    return os.path.join(os.getcwd(), "examples", "content_factory", "backlog.md")


def _parse_backlog(content: str) -> list[dict]:
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


@tool
def read_backlog(status: str = "READY", limit: int = 1) -> dict:
    """Read backlog entries filtered by status.

    :param status: Backlog status to include.
    :param limit: Maximum number of matching entries to return.
    :returns: Matching entries and counts by status.
    """
    try:
        with open(_backlog_path(), encoding="utf-8") as backlog_file:
            items = _parse_backlog(backlog_file.read())
    except OSError as error:
        return {"error": f"Unable to read backlog: {error}"}

    counts = {}
    for item in items:
        item_status = item.get("status", "")
        counts[item_status] = counts.get(item_status, 0) + 1

    return {
        "items": [item for item in items if item.get("status") == status][:limit],
        "counts": counts,
    }
