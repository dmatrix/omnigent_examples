"""Topic summarization tool."""

from __future__ import annotations

from omnigent_client.tools import tool


@tool
def summarize_topic(topic: str, max_points: int = 5) -> str:
    """
    Produce a structured summary of a topic.

    :param topic: The topic to summarize.
    :param max_points: Maximum number of bullet points (default 5).
    :returns: A formatted summary string.
    """
    return (
        f"## Summary: {topic}\n\n"
        f"Provide up to {max_points} key points about **{topic}**.\n\n"
        f"_(This is a placeholder — wire up a real retrieval backend "
        f"or let the LLM fill in the content.)_"
    )
