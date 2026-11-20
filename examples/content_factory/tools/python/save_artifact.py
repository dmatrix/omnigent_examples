"""Stage a content-factory artifact in the local artifacts directory."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from omnigent_client.tools import tool


def _artifacts_path() -> str:
    return os.path.join(os.getcwd(), "examples", "content_factory", "artifacts")


@tool
def save_artifact(kind: str, slug: str, content: str, variant: str = "") -> dict:
    """Save a staged artifact locally.

    :param kind: Artifact kind: cycle, outline, draft, or social.
    :param slug: Backlog slug associated with the artifact.
    :param content: Markdown content to save.
    :param variant: Social variant: x or linkedin.
    :returns: The saved path, byte count, and kind.
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
    else:
        return {"error": "kind must be cycle, outline, draft, or social with variant x or linkedin"}

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as artifact_file:
        artifact_file.write(content)
    return {"path": path, "bytes": len(content.encode("utf-8")), "kind": kind}
