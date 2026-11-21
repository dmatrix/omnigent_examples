"""Stage a content-factory artifact in the local artifacts directory."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from omnigent_client.tools import tool


def _artifacts_path() -> str:
    return os.path.join(os.getcwd(), "examples", "content_factory", "artifacts")


# Separator written before an appended cycle entry, so a day with several
# cycles reads as a sequence instead of one undifferentiated blob.
_CYCLE_ENTRY_SEPARATOR = "\n---\n\n*Cycle entry: `{slug}` — {timestamp}*\n\n"


def _cycle_entry_separator(path: str, slug: str) -> str:
    """Build the break that precedes an appended cycle entry.

    Prepends a newline only when the existing log does not already end with
    one, so the rule renders as a rule rather than drifting into the previous
    entry's last paragraph.
    """
    with open(path, "rb") as existing:
        existing.seek(-1, os.SEEK_END)
        ends_with_newline = existing.read(1) == b"\n"
    separator = _CYCLE_ENTRY_SEPARATOR.format(
        slug=slug,
        timestamp=f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}",
    )
    return separator if ends_with_newline else "\n" + separator


@tool
def save_artifact(kind: str, slug: str, content: str, variant: str = "") -> dict:
    """Save a staged artifact locally.

    :param kind: Artifact kind: cycle, outline, draft, social, or dashboard.
    :param slug: Backlog slug associated with the artifact.
    :param content: Markdown content to save.
    :param variant: Social variant: x or linkedin.
    :returns: A dict of ``path``, ``bytes`` and ``kind``. ``bytes`` is the size
        of the file at ``path`` AFTER this call, not the size of ``content``.
        The two differ only for ``kind="cycle"``, which appends: a day's
        cycle log accumulates one entry per cycle, so its reported size grows
        with each call. For ``outline``, ``draft`` and ``social`` the file is
        truncated and rewritten, so the resulting size equals the content size
        as before. ``dashboard`` also overwrites because it is a current-state
        snapshot at ``artifacts/dashboard.md``.
    """
    artifacts = _artifacts_path()
    if kind == "cycle":
        path = os.path.join(artifacts, "cycles", f"{datetime.now(timezone.utc):%Y-%m-%d}-cycle.md")
    elif kind == "outline":
        path = os.path.join(artifacts, "outlines", f"{slug}.md")
    elif kind == "draft":
        path = os.path.join(artifacts, "drafts", f"{slug}.md")
    elif kind == "social" and variant in ("x", "linkedin"):
        path = os.path.join(artifacts, "social", f"{slug}-{variant}.md")
    elif kind == "dashboard":
        path = os.path.join(artifacts, "dashboard.md")
    else:
        return {
            "error": "kind must be cycle, outline, draft, dashboard, or social with variant x or linkedin"
        }

    os.makedirs(os.path.dirname(path), exist_ok=True)
    if kind == "cycle":
        # Cycle logs are keyed by UTC date, and a day can run more than one
        # cycle. Truncating here destroyed every earlier entry for the day, so
        # the log is appended instead and each entry is separated.
        existing_bytes = os.path.getsize(path) if os.path.isfile(path) else 0
        with open(path, "a", encoding="utf-8", newline="") as artifact_file:
            if existing_bytes:
                artifact_file.write(_cycle_entry_separator(path, slug))
            artifact_file.write(content)
    else:
        # Outlines, drafts, social posts and the dashboard SHOULD be
        # overwritten: revised state replaces the older snapshot.
        with open(path, "w", encoding="utf-8", newline="") as artifact_file:
            artifact_file.write(content)
    return {"path": path, "bytes": os.path.getsize(path), "kind": kind}
