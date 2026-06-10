"""Greeting tool."""

from __future__ import annotations

from omnigents_client.tools import tool


@tool
def greet(name: str) -> str:
    """
    Greet someone by name.

    :param name: The person's name.
    :returns: A greeting string.
    """
    return f"Yo yo yo, what's crackin' {name}! Welcome to the party! 🎉"


@tool
def hello_world() -> str:
    """
    Return a classic Hello, World! greeting.

    :returns: The string ``"Hello, World!"``.
    """
    return "Hello, World!"
