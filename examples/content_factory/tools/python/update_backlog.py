"""Update one content-factory backlog entry's status in place."""

from __future__ import annotations

import os
import re

from omnigent_client.tools import tool


VALID_STATUSES = ("READY", "DRAFTED", "EDITED", "APPROVED", "PUBLISHED")


def _backlog_path() -> str:
    return os.path.join(os.getcwd(), "examples", "content_factory", "backlog.md")


@tool
def update_backlog(slug: str, status: str) -> dict:
    """Update a backlog entry's status without reformatting other entries.

    :param slug: Slug of the entry to update.
    :param status: New status, one of READY through PUBLISHED.
    :returns: The old and new status, or a clear error dict.
    """
    if status not in VALID_STATUSES:
        return {"error": f"Unknown status: {status}. Valid statuses: {', '.join(VALID_STATUSES)}"}

    try:
        with open(_backlog_path(), encoding="utf-8", newline="") as backlog_file:
            content = backlog_file.read()
    except OSError as error:
        return {"error": f"Unable to read backlog: {error}"}

    pattern = re.compile(
        rf"(?ms)(^## {re.escape(slug)}\r?\n(?:(?!^## ).)*?^- status: )([^\r\n]+)(?=\r?\n)"
    )
    match = pattern.search(content)
    if match is None:
        if re.search(rf"(?m)^## {re.escape(slug)}\r?$", content):
            return {"error": f"Backlog entry has no status: {slug}"}
        return {"error": f"Unknown backlog slug: {slug}"}

    old_status = match.group(2)
    updated_content = content[: match.start(2)] + status + content[match.end(2) :]
    try:
        with open(_backlog_path(), "w", encoding="utf-8", newline="") as backlog_file:
            backlog_file.write(updated_content)
    except OSError as error:
        return {"error": f"Unable to update backlog: {error}"}

    return {"slug": slug, "old_status": old_status, "new_status": status}
