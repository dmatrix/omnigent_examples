"""Promote staged content-factory artifacts into the local published directory."""

from __future__ import annotations

import glob
import os
import shutil

from omnigent_client.tools import tool


def _artifacts_path() -> str:
    return os.path.join(os.getcwd(), "examples", "content_factory", "artifacts")


@tool
def publish_content(slug: str) -> dict:
    """Publish a staged draft and social posts to the local published directory.

    :param slug: Backlog slug whose staged artifacts should be published.
    :returns: The slug and paths of promoted artifacts.
    """
    artifacts = _artifacts_path()
    draft_path = os.path.join(artifacts, "drafts", f"{slug}.md")
    source_paths = [draft_path, *sorted(glob.glob(os.path.join(artifacts, "social", f"{slug}-*.md")))]
    existing_paths = [path for path in source_paths if os.path.isfile(path)]
    if not os.path.isfile(draft_path):
        return {"error": f"Draft artifact not found for slug: {slug}"}

    destination = os.path.join(artifacts, "published", slug)
    os.makedirs(destination, exist_ok=True)
    published = []
    for source_path in existing_paths:
        target_path = os.path.join(destination, os.path.basename(source_path))
        shutil.copyfile(source_path, target_path)
        published.append(target_path)
    return {"slug": slug, "published": published}
