"""Minimal test tool."""

from __future__ import annotations

from omniagents_client.tools import tool


@tool
def hello(name: str) -> str:
    """
    Say hello.

    :param name: Who to greet.
    :returns: A greeting.
    """
    return f"Hello, {name}!"
