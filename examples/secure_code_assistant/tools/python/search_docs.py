"""Web documentation search tool."""

from __future__ import annotations

from omnigents_client.tools import tool


@tool
def search_docs(query: str) -> str:
    """Search the web for technical documentation and code examples.

    :param query: Search query for documentation.
    :returns: Search results as text.
    """
    return f"[search_docs] Searching for: {query}"
