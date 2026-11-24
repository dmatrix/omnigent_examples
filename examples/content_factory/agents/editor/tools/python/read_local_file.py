import os
from omnigent_client.tools import tool


@tool
def read_local_file(path: str) -> str:
    """
    Read the contents of a local workspace file.

    Resolves workspace-relative paths from ``os.getcwd()``, matching the
    behaviour of every other tool in the content-factory bundle (the agent
    bundle is copied to a temp directory, so __file__ is not reliable —
    always use getcwd()).

    Args:
        path: Workspace-relative or absolute path to the file.

    Returns:
        The file contents as a string, or an error message.
    """
    if not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)

    if not os.path.exists(path):
        return f"Error: file not found: {path}"

    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except Exception as exc:
        return f"Error reading {path}: {exc}"
