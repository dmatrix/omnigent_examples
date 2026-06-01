"""Greeting tool."""

from __future__ import annotations

from omniagents_client.tools import tool


@tool
def greet(name: str) -> str:
    """
    Greet someone by name.

    :param name: The person's name.
    :returns: A greeting string.
    """
    return f"Yo yo yo, what's crackin' {name}! Welcome to the party!"
