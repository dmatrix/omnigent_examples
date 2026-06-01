"""Reverse string tool."""

from __future__ import annotations

from omniagents_client.tools import tool


@tool
def reverse_string(text: str) -> str:
    """
    Reverse a string.

    :param text: The string to reverse.
    :returns: The input string with its characters in reverse order.
    """
    return text[::-1]
