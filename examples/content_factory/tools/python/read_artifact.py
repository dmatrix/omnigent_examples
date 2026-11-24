import os
import glob
from omnigent_client.tools import tool


@tool
def read_artifact(slug: str, kind: str, variant: str = "") -> str:
    """
    Read a staged artifact from disk and return its content.

    :param slug: Backlog slug, e.g. 'contextual-policies'.
                 Pass 'dashboard' when kind='dashboard'.
    :param kind: Artifact kind: outline, draft, social, cycle, or dashboard.
    :param variant: Required when kind='social' — 'x' or 'linkedin'.
    :returns: File content as a string, or an error listing files that ARE present.
    """
    artifacts_dir = os.path.join(
        os.getcwd(), "examples", "content_factory", "artifacts"
    )

    # Filename convention must mirror what save_artifact writes
    if kind == "dashboard":
        filename = "dashboard.md"
    elif kind == "social":
        if not variant:
            return "Error: variant ('x' or 'linkedin') is required when kind='social'."
        filename = f"{slug}-{variant}.md"
    elif kind == "cycle":
        # cycle log is keyed by UTC date, one file accumulates all slugs for the day
        from datetime import datetime, timezone
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"{date_str}-cycle.md"
    else:
        # outline, draft
        filename = f"{slug}-{kind}.md"

    path = os.path.join(artifacts_dir, filename)

    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    # Not found — list what IS there so we can correct the convention if needed
    available = sorted(glob.glob(os.path.join(artifacts_dir, "*.md")))
    names = [os.path.basename(p) for p in available] or ["(none)"]
    return (
        f"Artifact not found: {path}\n"
        f"Files present in artifacts/: {', '.join(names)}"
    )
