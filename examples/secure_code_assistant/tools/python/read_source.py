"""Source file reader tool."""

from __future__ import annotations

from omnigents_client.tools import tool


@tool
def read_source(file_path: str) -> str:
    """Read a source file from the project directory.

    :param file_path: Relative path to the file to read.
    :returns: The file contents as a string.
    """
    import os

    full_path = os.path.join(os.getcwd(), file_path)
    with open(full_path) as f:
        return f.read()
