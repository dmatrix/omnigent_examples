"""In-memory FAQ knowledge base for evaluator proof-of-concept."""

from __future__ import annotations

from omnigent_client.tools import tool

FAQ_DATA = {
    "pricing": "Our plans start at $9.99/month (Basic), $19.99/month (Pro), and $49.99/month (Enterprise).",
    "refunds": "Full refunds within 30 days. After 30 days, prorated refunds only. Contact support@example.com.",
    "hours": "Customer support: Mon-Fri 9am-6pm EST. Emergency line: 24/7.",
    "shipping": "Free shipping on orders over $50. Standard delivery: 3-5 business days. Express: 1-2 days.",
    "contact": "Email: support@example.com. Phone: 1-800-555-0199. Chat: available on our website.",
}


@tool
def lookup_faq(topic: str) -> str:
    """
    Look up an answer from the company FAQ knowledge base.

    :param topic: The FAQ topic to look up (e.g. "pricing", "refunds", "shipping").
    :returns: The FAQ answer, or a not-found message with available topics.
    """
    topic_lower = topic.lower().strip()
    for key, value in FAQ_DATA.items():
        if key in topic_lower or topic_lower in key:
            return f"FAQ ({key}): {value}"
    available = ", ".join(FAQ_DATA.keys())
    return f"No FAQ entry found for '{topic}'. Available topics: {available}"
