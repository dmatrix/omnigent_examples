"""Word count tool."""

from __future__ import annotations

from omniagents_client.tools import tool


@tool
def word_count(text: str) -> dict[str, int]:
    """
    Count words, characters, and unique words in a string.

    :param text: The input string to analyse,
        e.g. ``"the quick brown fox jumps over the lazy dog"``.
    :returns: A dict with three integer keys:

        - ``total_words``  — number of whitespace-delimited tokens.
        - ``total_chars``  — total number of characters (including spaces).
        - ``unique_words`` — number of distinct lowercase words.
    """
    words = text.split()
    return {
        "total_words": len(words),
        "total_chars": len(text),
        "unique_words": len({w.lower() for w in words}),
    }
